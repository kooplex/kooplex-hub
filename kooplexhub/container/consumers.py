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

from hub.util import is_model_field, SyncSkeleton, AsyncSkeleton

logger = logging.getLogger(__name__)

#################
# FIXME put somewhere common 



# Custom JSON encoder
class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Image):
            return { "image": obj.id }
        elif isinstance(obj, QuerySet):
            if obj.model == ProjectContainerBinding:
                return { "projects": [ b.project.id for b in obj ] }
            elif obj.model == CourseContainerBinding:
                return { "courses":  [ b.course.id for b in obj ] }
            elif obj.model == VolumeContainerBinding:
                return { "volumes": [ b.volume.id for b in obj ] }
        return super().default(obj)
#################

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
    identifier_='container'
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


class ContainerConfigConsumer(CSyncSkeleton):
    def _msg(self, container, message, errors={}, reload=False):
        message_back = {
            "container_id": container.id,
            "feedback": message,
            "response": "reloadpage" if reload else render_to_string("container.html", {"container": container, "errors": errors}),
        }
        logger.debug(message_back["feedback"])
        self.send(text_data=json.dumps(message_back))

    def _chg_image(self, container, image):
        old_value=container.image.name
        container.image=image
        container.save()
        m=f"Environment image of {container.name} changed from {old_value} to {image.name}"
        container.mark_restart(m)
        self._msg(container, m)

    def _chg_bindings(self, container, ids, obj_type, bind_type, attr, m):
        a=[]
        r=[]
        for o in obj_type.objects.filter(id__in = ids):
            b, _=bind_type.objects.get_or_create(**{attr: o, 'container': container})
            a.append(getattr(b, attr).name)
        for b in bind_type.objects.filter(container = container).exclude(**{f"{attr}__id__in": ids}):
            r.append(getattr(b, attr).name)
            b.delete()
        if a:
            m += "added " + ", ".join(a) + "\n"
        if r:
            m += "removed " + ", ".join(r) + "\n"
        if a or r:
            container.mark_restart(m)
            self._msg(container, m)


    def receive(self, text_data):
        parsed = json.loads(text_data)
        logger.debug(parsed)
        assert parsed.get('request')=='configure-container', "wrong request"
        failed={}
        pk=parsed.get('pk')
        changes=parsed.get('changes')
        if pk == "None":
            reloadpage=True
            container=Container(name=changes['name'], user_id=self.get_userid(), image_id=changes['image'])
            container.save()
            self._msg(container, f"New environment {container.name} is created", reload=True)
        else:
            cid=int(pk)
            container=self.get_container(cid)
        # Iterate over the changes and try to update the model instance
        for field, new_value in changes.items():
            if field == 'image' and pk != "None":
                new_value=Image.objects.get(id=new_value)
                self._chg_image(container, new_value)
            elif field == 'projects':
                self._chg_bindings(container, new_value, Project, ProjectContainerBinding, 'project', f"Project mounts of environment {container.name} changed:\n")
            elif field == 'courses':
                self._chg_bindings(container, new_value, Course, CourseContainerBinding, 'course', f"Course mounts of environment {container.name} changed:\n")
            elif field == 'volumes':
                self._chg_bindings(container, new_value, Volume, VolumeContainerBinding, 'volume', f"Storage mounts of environment {container.name} changed:\n")
            # Check if the field is a valid attribute of the model
            elif is_model_field(container, field):
                old_value = getattr(container, field)
                try:
                    if field in ['start_teleport', 'start_seafile']:
                        _what=field.split('_')[-1]
                        m=f"The {_what} in environment {container.name} requested state change"
                        new_value=new_value=="grant"
                        container.mark_restart(m)
                    else:
                        m=f"Attribute {field} of environment {container.name} changed from {getattr(container, field)} to {new_value}"
                    # Try assigning the new value to the model's field
                    setattr(container, field, new_value)
                    # Run Django's model validation for the field
                    container.full_clean(validate_unique=True, exclude=[f for f in changes.keys() if f != field])
                    self._msg(container, m)
                    container.save()
                except ValidationError as e:
                    # Validation failed, record the error message
                    failed[field] = { "error": str(e), "value": old_value }
                    self._msg(container, f"Problem configuring environment {container.name}", errors=failed)
            else:
                # Attribute does not exist on the model
                logger.error(f"Container model attribute {field} does not exist.")
                

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
            from kooplexhub.settings import KOOPLEX
            kubernetes = KOOPLEX.get('kubernetes',{}).get('resources',{}).get('maxrequests',{})
            resp.update({
             "feedback" : f"Node resource information for defaults is updated",
             "avail_cpu": kubernetes.get('cpu',1),
             "avail_memory": kubernetes.get('memory',2),
             "avail_gpu": kubernetes.get('nvidia.com/gpu',0),
                })
        logger.debug(f"fetch {node} -> {resp}")
        self.send(text_data = json.dumps(resp))



