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

from container.forms import FormContainer
from .lib import Cluster

from .tasks import *
from .models import Image

from hub.util import SyncSkeleton, AsyncSkeleton

from .conf import CONTAINER_SETTINGS

logger = logging.getLogger(__name__)


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



class ContainerConfigHandler:
    def __init__(self, instance):
        self.instance = instance
        self.attribute_handlers = {
            'name': (False, self.handle_name_update),
            'image': (False, self.handle_image_update),
            'node': (True, self.handle_resource_update),
            'cpurequest': (True, self.handle_resource_update),
            'gpurequest': (True, self.handle_resource_update),
            'memoryrequest': (True, self.handle_resource_update),
            'idletime': (True, self.handle_resource_update),
            'start_teleport': (True, self.handle_onoff_update),
            'start_seafile': (True, self.handle_onoff_update),
            'projects': (True, self.handle_mounts_update),
            'courses': (True, self.handle_mounts_update),
            'volumes': (True, self.handle_mounts_update),
        }

    def handle_attribute(self, attribute_name, new_value):
        pass_attribute, handler = self.attribute_handlers.get(attribute_name)
        if handler and pass_attribute:
            return handler(attribute_name, new_value)
        elif handler:
            return handler(new_value)
        else:
            logger.critical(f"No handler for container configuration attribute: {attribute_name}")

    def handle_name_update(self, new_value):
        from .templatetags.container_tags import render_name
        old_value = self.instance.name
        self.instance.name = new_value
        try:
            self.instance.full_clean()
            self.instance.save()
            return f"name changed from {old_value} to {new_value}", {f"[data-name=name][data-pk={self.instance.pk}][data-model=container]": render_name(self.instance)}
        except ValidationError as e:
            self.instance.name = old_value
            return str(e), {f"[data-name=name][data-pk={self.instance.pk}][data-model=container]": render_name(self.instance)}

    def handle_image_update(self, new_value):
        from .templatetags.container_buttons import button_image
        old_value = self.instance.image.name
        image = Image.objects.get(id=new_value)
        self.instance.image = image
        self.instance.save()
        return f"image changed from {old_value} to {image.name}", {f"[data-name=image][data-pk={self.instance.pk}][data-model=container]": button_image(self.instance, 'container', 'image')}

    def handle_resource_update(self, attribute, new_value):
        from .templatetags.container_buttons import button_resources
        old_value = getattr(self.instance, attribute)
        setattr(self.instance, attribute, new_value)
        self.instance.save()
        return f"{attribute} request changed from {old_value} to {new_value}", {f"[data-name=resources][data-pk={self.instance.pk}][data-model=container]": button_resources(self.instance)}

    def handle_onoff_update(self, attribute, new_value):
        from .templatetags.container_buttons import button_seafile, button_teleport
        old_value = getattr(self.instance, attribute)
        _what=attribute.split('_')[-1]
        _newstate = 'enabled' if new_value else 'disabled'
        setattr(self.instance, attribute, new_value)
        m=f"{_what} is {_newstate}"
        self.instance.mark_restart(m)
        self.instance.save()
        render_map = {
            'start_teleport': button_teleport,
            'start_seafile': button_seafile,
        }
        if render:=render_map.get(attribute):
            w = render(self.instance)
        else:
            w = None
        return m, {f"[data-name={attribute}][data-pk={self.instance.pk}][data-model=container]": w}

    def handle_mounts_update(self, attribute, new_value):
        from .templatetags.container_buttons import button_mount
        mapper = {
            'projects': (Project, ProjectContainerBinding),
            'courses':  (Course, CourseContainerBinding),
            'volumes':  (Volume, VolumeContainerBinding),
        }
        obj_type, bind_type = mapper.get(attribute)
        attribute=attribute[:-1] # split off s
        a=[]
        r=[]
        m=f"{attribute} mounts changed: "
        n = lambda b: getattr(b, attribute).folder if attribute == 'volume' else getattr(b, attribute).name
        for o in obj_type.objects.filter(id__in = new_value):
            b, _=bind_type.objects.get_or_create(**{attribute: o, 'container': self.instance})
            a.append(n(b))
        for b in bind_type.objects.filter(container=self.instance).exclude(**{f"{attribute}__id__in": new_value}):
            r.append(n(b))
            b.delete()
        if a:
            m += "added " + ", ".join(a) + "\n"
        if r:
            m += "removed " + ", ".join(r) + "\n"
        if a or r:
            return m, {f"[data-name=mount][data-pk={self.instance.pk}][data-model=container]": button_mount(self.instance)}
        else:
            return "", {}


class ContainerConfigConsumer(CSyncSkeleton):
    def receive(self, text_data):
        parsed = json.loads(text_data)
        logger.debug(parsed)
        request = parsed.get('request')
        if request == "create-container":
            container=Container(name=parsed['name'], user_id=self.get_userid(), image_id=parsed['image'])
            container.save()
            self.send(text_data=json.dumps({
                'feedback': f"New environment {container.name} is created",
                'reload_page': True,
            }))
            configurator = ContainerConfigHandler(container)
            changes = { k: parsed[k] for k in configurator.attribute_handlers.keys() if k in parsed and not k in ["name", "image"] }
        elif request =='configure-container':
            pk=parsed.get('pk')
            changes=parsed.get('changes')
            cid=int(pk)
            container=self.get_container(cid)
            configurator = ContainerConfigHandler(container)
        elif request =='update-widget':
            field=parsed.get('field')
            if field=='start_seafile':
                from .templatetags.container_buttons import button_seafile
                self.send(text_data=json.dumps({'replace_widgets': {f"[data-name=start_seafile][data-pk=None][data-model=container]": button_seafile(value=parsed.get('value'))}}))
            elif field=='start_teleport':
                from .templatetags.container_buttons import button_teleport
                self.send(text_data=json.dumps({'replace_widgets': {f"[data-name=start_teleport][data-pk=None][data-model=container]": button_teleport(value=parsed.get('value'))}}))
            elif field=='image':
                from .templatetags.container_buttons import button_image
                image = Image.objects.get(id=parsed.get('value'))
                self.send(text_data=json.dumps({'replace_widgets': {f"[data-name=image][data-pk=None][data-model=container]": button_image(model='container', attr='image', value=image)}}))
            elif field=='node':
                from .templatetags.container_buttons import button_resource_node
                self.send(text_data=json.dumps({'replace_widgets': {f"[data-name=node][data-pk=None][data-model=container]": button_resource_node(value=parsed.get('value'))}}))
            elif field=='cpurequest':
                from .templatetags.container_buttons import button_resource_cpurequest
                self.send(text_data=json.dumps({'replace_widgets': {f"[data-name=cpurequest][data-pk=None][data-model=container]": button_resource_cpurequest(value=parsed.get('value'))}}))
            elif field=='gpurequest':
                from .templatetags.container_buttons import button_resource_gpurequest
                self.send(text_data=json.dumps({'replace_widgets': {f"[data-name=gpurequest][data-pk=None][data-model=container]": button_resource_gpurequest(value=parsed.get('value'))}}))
            elif field=='memoryrequest':
                from .templatetags.container_buttons import button_resource_memoryrequest
                self.send(text_data=json.dumps({'replace_widgets': {f"[data-name=memoryrequest][data-pk=None][data-model=container]": button_resource_memoryrequest(value=parsed.get('value'))}}))
            elif field=='idletime':
                from .templatetags.container_buttons import button_resource_idletime
                self.send(text_data=json.dumps({'replace_widgets': {f"[data-name=idletime][data-pk=None][data-model=container]": button_resource_idletime(value=parsed.get('value'))}}))
            elif field=='projects':
                from .templatetags.container_buttons import button_mount_projects
                self.send(text_data=json.dumps({'replace_widgets': {f"[data-name=projects][data-pk=None][data-model=container]": button_mount_projects(value=parsed.get('value'))}}))
            elif field=='courses':
                from .templatetags.container_buttons import button_mount_courses
                self.send(text_data=json.dumps({'replace_widgets': {f"[data-name=courses][data-pk=None][data-model=container]": button_mount_courses(value=parsed.get('value'))}}))
            elif field=='volumes':
                from .templatetags.container_buttons import button_mount_volumes
                self.send(text_data=json.dumps({'replace_widgets': {f"[data-name=volumes][data-pk=None][data-model=container]": button_mount_volumes(value=parsed.get('value'))}}))


            else:
                logger.critical(f"unknown {field}")

            return
        else:
            logger.error(f"wrong request: {request}")
            return
        failed={}
        # Iterate over the changes and try to update the model instance
        widgets={}
        messages=[]
        for field, new_value in changes.items():
            m, w = configurator.handle_attribute(field, new_value)
            messages.append(m)
            widgets.update(w)
        if messages:
            self.send(text_data=json.dumps({
                'feedback': f"Container {container.name} is configured: " + ",".join(messages) + ".",
                'replace_widgets': widgets,
            }))



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



