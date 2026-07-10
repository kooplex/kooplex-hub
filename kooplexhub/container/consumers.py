import logging
import json
import threading

from asgiref.sync import sync_to_async
from django.utils.html import format_html
from django.core.exceptions import ValidationError
from django.template.loader import render_to_string

from django.db.models.query import QuerySet
from container.models import Container
from project.models import Project, ProjectContainerBinding
from education.models import Course, CourseContainerBinding
from volume.models import Volume, VolumeContainerBinding

from channels.generic.websocket import AsyncJsonWebsocketConsumer

from .lib import Cluster

from .tasks import *
from .models import Image

from hub.util import SyncSkeleton, AsyncSkeleton

from .conf import CONTAINER_SETTINGS

logger = logging.getLogger(__name__)

##############################################
from django.db import transaction
from django.db import models

# which fields touch which fragments
FRAG_BY_FIELD = {
    "name": {"name"},
    "image": {"image", "restarter"},
    "start_teleport": {"teleport", "restarter"},
    "start_seafile": {"seafile", "restarter"},
    "state": {"stateindicator", "logfetcher"},
    "state_backend": {"stateindicator", "logfetcher"},
    "restart_reasons": {"restarter"},
    "node": {"node", "restarter"},
    "cpurequest": {"cpu", "restarter"},
    "cpuusage": {"cpu"},
    "gpurequest": {"gpu", "restarter"},
    "memoryrequest": {"mem", "restarter"},
    "memoryusage": {"mem"},
    "idletime": {"idle", "restarter"},
    "idle": {"idle"},
    "projects": {"projects", "restarter"},
    "courses": {"courses", "restarter"},
    "volumes": {"volumes", "restarter"},
}

def fragments_for(changes):
    targets = set()
    for fld in changes.keys():
        targets |= FRAG_BY_FIELD.get(fld, set())
    return targets

def render_fragment(key, **kw):
    if obj:=kw.get('obj'):
        pk=obj.pk
        ctx={
            'pk': pk,
            'container': obj,
        }
    else:
        pk=None
        ctx={
            'pk': pk,
            'value': kw.get('value'),
        }
    error=kw.get('errors')
#DEPRECATED    if key == "name":
#DEPRECATED        from .templatetags.container_tags import render_name
#DEPRECATED        if error:
#DEPRECATED            ctx.update({
#DEPRECATED                'error': ', '.join(error['name']),
#DEPRECATED                'original_value': kw.get('original_value'),
#DEPRECATED            })
#DEPRECATED        html=render_name(**ctx)
#DEPRECATED        ref=f"[data-name=name][data-pk={pk}][data-model=container]"
#DEPRECATED        return ref, html
    if key == "image":
        from .templatetags.container_buttons import button_image
        html=button_image(obj, 'container', 'image', **ctx)
        ref=f"[data-name=image][data-pk={pk}][data-model=container]"
        return ref, html
    if key == "seafile":
        from .templatetags.container_buttons import button_seafile
        html=button_seafile(**ctx)
        ref=f"[data-name=start_seafile][data-pk={pk}][data-model=container]"
        return ref, html
    if key == "teleport":
        from .templatetags.container_buttons import button_teleport
        html=button_teleport(**ctx)
        ref=f"[data-name=start_teleport][data-pk={pk}][data-model=container]"
        return ref, html
    if key == "node":
        html=render_to_string("container/resources/node.html", {'container': obj})
        ref=f"[data-pk={pk}][data-name=node]"
        return ref, html
    if key == "cpu":
        html=render_to_string("container/resources/cpu.html", {'container': obj})
        ref=f"[data-pk={pk}][data-name=cpu]"
        return ref, html
    if key == "gpu":
        html=render_to_string("container/resources/gpu.html", {'container': obj})
        ref=f"[data-pk={pk}][data-name=gpu]"
        return ref, html
    if key == "mem":
        html=render_to_string("container/resources/memory.html", {'container': obj})
        ref=f"[data-pk={pk}][data-name=memory]"
        return ref, html
    if key == "idle":
        html=render_to_string("container/resources/idle.html", {'container': obj})
        ref=f"[data-pk={pk}][data-name=idletime]"
        return ref, html
    if key == "projects":
        from .templatetags.container_buttons import button_mount_projects
        html=button_mount_projects(**ctx)
        ref=f"[data-name=projects][data-pk={pk}][data-model=container]"
        return ref, html
    if key == "courses":
        from .templatetags.container_buttons import button_mount_courses
        html=button_mount_courses(**ctx)
        ref=f"[data-name=courses][data-pk={pk}][data-model=container]"
        return ref, html
    if key == "volumes":
        from .templatetags.container_buttons import button_mount_volumes
        html=button_mount_volumes(**ctx)
        ref=f"[data-name=volumes][data-pk={pk}][data-model=container]"
        return ref, html

    if key == "restarter":
        html=render_to_string("container/button/restart.html", {'container': obj})
        ref=f"[data-action=restart][data-pk={pk}]"
        return ref, html

    raise KeyError(key)

@transaction.atomic
def update_fragments(model_cls, pk, changes, field_map=None, fk_hooks=None):
    obj = model_cls.objects.select_for_update().get(pk=pk)
    originals={}
    field_map = field_map or {}
    fk_hooks = fk_hooks or {}
    for key, val in changes.items():
        fld = field_map.get(key, key)
        if not hasattr(obj, fld):
            continue
        if fld in fk_hooks:
            getter, setter = fk_hooks[fld]
            originals[fld] = getter(obj)
            setter(obj, val)
            continue
        field_obj = model_cls._meta.get_field(fld)
        if isinstance(field_obj, models.ForeignKey):
            originals[fld] = getattr(obj, fld + "_id")
            setattr(obj, fld + "_id", val)
        else:
            originals[fld]=getattr(obj, fld)
            setattr(obj, fld, val)

    try:
        obj.full_clean()
    except ValidationError as e:
        keys = fragments_for(changes)
        replace = dict([
            render_fragment(
                k, 
                obj=obj, 
                original_value=originals[field_map.get(k, k)], 
                errors=e.message_dict,
            )
            for k in keys 
        ])
        return {"replace_widgets": replace}

    obj.save()

    keys = fragments_for(changes)
    replace = dict([
        render_fragment(
            k,
            obj=obj,
            original_value=originals.get(field_map.get(k, k))
        )
        for k in keys
    ])
    return {"replace_widgets": replace}
##############################################


class CSyncSkeleton(SyncSkeleton):
    def get_container(self, container_id):
        return Container.objects.get(id = container_id, user__id = self.userid)

class ContainerFetchlogConsumer(CSyncSkeleton):
    def receive(self, text_data):
        parsed = json.loads(text_data)
        logger.debug(parsed)
        cid = int(parsed.get('pk'))
        container = self.get_container(cid)
        request = parsed.get('request')
        assert request == 'container-log', "wrong request"
        resp = container.retrieve_log()
        logger.debug(f"fetch {container} -> {resp[:10]}...")
        self.send(text_data = json.dumps({ 'podlog': resp}))


class ContainerControlConsumer(AsyncSkeleton):
    identifier_='container-{user.id}'
    def get_container(self, container_id):
        return sync_to_async(Container.objects.get)(id = container_id, user__id = self.userid)

    async def receive(self, text_data):
        parsed = json.loads(text_data)
        logger.debug(parsed)
        cid = int(parsed.get('pk'))
        container = await self.get_container(cid)
        request = parsed.get('request')
        if request == 'start':
            await self.send(text_data=json.dumps({"feedback": f'Starting container {container.name}. Keep calm until its state is finalized.' }))
            await sync_to_async(container.start)()
        elif request == 'stop':
            await self.send(text_data=json.dumps({"feedback": f'Stopping container {container.name}.' }))
            await sync_to_async(container.stop)()
        elif request == 'restart':
            await self.send(text_data=json.dumps({"feedback": f'Restarting container {container.name}' }))
            await sync_to_async(container.restart)()
        else:
            logger.error(f'wrong ws call request: {request}')



class ContainerLiveConsumer(AsyncJsonWebsocketConsumer):
    """
    Live invalidation feed for container/environment pages.

    This consumer does not perform mutations.
    It only receives server-side live events and forwards them to browsers.
    """

    async def connect(self):
        user = self.scope.get("user")

        if user is None or not user.is_authenticated:
            await self.close(code=4401)
            return

        self.user = user
        self.user_group_name = self.group_name_for_user(user.pk)

        await self.channel_layer.group_add(
            self.user_group_name,
            self.channel_name,
        )

        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "user_group_name"):
            await self.channel_layer.group_discard(
                self.user_group_name,
                self.channel_name,
            )

    @staticmethod
    def group_name_for_user(user_id):
        return f"container-live-user-{user_id}"

    async def receive_json(self, content, **kwargs):
        """
        Browser-to-server messages are intentionally ignored for now.

        Later this could accept pings, client_id registration, etc.
        """
        return

    async def container_live_event(self, event):
        """
        Handler for channel layer events.

        group_send must use:
            {"type": "container.live_event", "payload": {...}}

        Channels maps "container.live_event" -> container_live_event().
        """
        await self.send_json(event["payload"])

    @staticmethod
    def group_name_for_user(user_id):
        return f"container-live-user-{user_id}"





class MonitorConsumer(SyncSkeleton):
    def receive(self, text_data):
        parsed = json.loads(text_data)
        logger.debug(parsed)
        request = parsed.get('request')
        assert request == 'monitor-node', "wrong request"
        node = parsed.get('node')
        resp = {
            'request': request,
            'node': node,
        }
        if node:
            api = Cluster()
            api.query_nodes_status(node_list=[node], reset=True)
            api.query_pods_status(field=["spec.nodeName=",node], reset=True)
            api.resources_summary()
            resp.update( api.get_data() )
            resp["feedback"] = f"Node resource information for {node} is updated"
        else:
            node = "default"
            resp.update({
             "feedback" : f"Node resource information for defaults is updated",
             "avail_cpu": CONTAINER_SETTINGS['kubernetes']['resources']['max_cpu'],
             "avail_memory": CONTAINER_SETTINGS['kubernetes']['resources']['max_memory'],
             "avail_gpu": CONTAINER_SETTINGS['kubernetes']['resources']['max_gpu'],
                })
        logger.debug(f"fetch {node} -> {resp}")
        self.send(text_data = json.dumps(resp))



