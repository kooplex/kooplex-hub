import logging
import json
import threading

from channels.generic.websocket import WebsocketConsumer
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from django.utils.html import format_html
from django.core.exceptions import ValidationError
from django.core.exceptions import FieldDoesNotExist

from django.db.models.query import QuerySet
from container.models import Container
from project.models import Project, ProjectContainerBinding
from education.models import Course, CourseContainerBinding
from volume.models import Volume, VolumeContainerBinding

from container.forms import FormContainer
from django.template.loader import render_to_string
from .lib import Cluster

from .tasks import *

logger = logging.getLogger(__name__)

#################
# FIXME put somewhere common 

def model_field(instance, attr_name):
    # Get the class of the instance
    cls = instance.__class__
    # Check if the attribute is a Django model field
    try:
        instance._meta.get_field(attr_name)
        return True
    except FieldDoesNotExist:
        pass
    return False


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




class SyncSkeleton(WebsocketConsumer):
    def connect(self):
        if not self.scope['user'].is_authenticated:
            return
        self.accept()
        self.userid = int(self.scope["url_route"]["kwargs"].get('userid'))
        assert self.scope['user'].id == self.userid, "not authorized"
#
#    def disconnect(self, close_code):
#        self.killed.set()
#
    def get_container(self, container_id):
        return Container.objects.get(id = container_id, user__id = self.userid)
    def get_userid(self):
        return self.userid

class ContainerFetchlogConsumer(SyncSkeleton):
    def receive(self, text_data):
        parsed = json.loads(text_data)
        logger.debug(parsed)
        cid = int(parsed.get('pk'))
        container = self.get_container(cid)
        request = parsed.get('request')
        assert request == 'container-log', "wrong request"
        resp = container.check_state(retrieve_log = True)
        logger.debug(f"fetch {container} -> {resp}")
        self.send(text_data = json.dumps(resp))


class ContainerControlConsumer(AsyncWebsocketConsumer):
    def get_container(self, container_id):
        return sync_to_async(Container.objects.get)(id = container_id, user__id = self.userid)

    async def connect(self):
        if not self.scope['user'].is_authenticated:
            return
        self.userid = int(self.scope["url_route"]["kwargs"].get('userid'))
        if self.scope['user'].id != self.userid: #not authorized
            return

        self.identifier = 'container'
        await self.channel_layer.group_add(self.identifier, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.identifier, self.channel_name)

    async def receive(self, text_data):
        parsed = json.loads(text_data)
        logger.debug(parsed)
        cid = int(parsed.get('pk'))
        container = await self.get_container(cid)
        request = parsed.get('request')
        if request == 'start':
            await self.send(text_data=json.dumps({"feedback": f'Starting container {container.name}. Keep calm until its state is finalized.' }))
            start_container(self.userid, container.id)
        elif request == 'stop':
            await self.send(text_data=json.dumps({"feedback": f'Stopping container {container.name}.' }))
            stop_container(self.userid, container.id)
        elif request == 'restart':
            await self.send(text_data=json.dumps({"feedback": f'Restarting container {container.name}' }))
            stop_container(self.userid, container.id)
            start_container(self.userid, container.id)
        else:
            logger.error(f'wrong ws call request: {request}')

    async def feedback(self, event):
        # Send message to WebSocket
        await self.send(text_data=json.dumps(event))


class ContainerConfigConsumer(SyncSkeleton):
    def receive(self, text_data):
        parsed = json.loads(text_data)
        logger.debug(parsed)
        assert parsed.get('request')=='configure-container', "wrong request"
        response = {
            "success": {},
            "failed": {},
        }
        pk = parsed.get('pk')
        changes = parsed.get('changes')
        if pk == "new":
            container=Container(name=changes['name'], user_id=self.get_userid(), image_id=changes['image'])
            container.save()
            response["reloadpage"]=True
        else:
            cid = int(parsed.get('pk'))
            container = self.get_container(cid)
        response["container_id"]=container.id
        restart=[]
        # Iterate over the changes and try to update the model instance
        for field, new_value in changes.items():
            if field == 'image':
                new_value=Image.objects.get(id=new_value)
            # Check if the field is a valid attribute of the model
            if model_field(container, field):
                old_value = getattr(container, field)
                try:
                    # Try assigning the new value to the model's field
                    setattr(container, field, new_value)
                    # Run Django's model validation for the field
                    container.full_clean(validate_unique=True, exclude=[f for f in changes.keys() if f != field])
                    # If no exception was raised, add it to the success response
                    response["success"][field] = new_value
                except ValidationError as e:
                    # Validation failed, record the error message
                    response["failed"][field] = { "error": str(e), "value": old_value }
            elif field == 'projects':
                for project in Project.objects.filter(id__in = new_value):
                    ProjectContainerBinding.objects.get_or_create(project = project, container = container)
                ProjectContainerBinding.objects.filter(container = container).exclude(project__id__in = new_value).delete()
                response["success"]['projects']=ProjectContainerBinding.objects.filter(container = container)
                restart.append("project mounts changed")
            elif field == 'courses':
                for course in Course.objects.filter(id__in = new_value):
                    CourseContainerBinding.objects.get_or_create(course = course, container = container)
                CourseContainerBinding.objects.filter(container = container).exclude(course__id__in = new_value).delete()
                response["success"]['courses']=CourseContainerBinding.objects.filter(container = container)
                restart.append("course mounts changed")
            elif field == 'volumes':
                for volume in Volume.objects.filter(id__in = new_value):
                    VolumeContainerBinding.objects.get_or_create(volume = volume, container = container)
                VolumeContainerBinding.objects.filter(container = container).exclude(volume__id__in = new_value).delete()
                response["success"]['volumes']=VolumeContainerBinding.objects.filter(container = container)
                restart.append("volume mounts changed")
            else:
                # Attribute does not exist on the model
                logger.error(f"Container model attribute {field} does not exist.")
        # Save the instance if there are any successful changes
        if response["success"]:
            container.save()
        if 'image' in changes.keys():
            restart.append("image changed")
        if 'start_teleport' in changes.keys():
            restart.append("teleport {}".format("enabled" if container.start_teleport else "disabled"))
        if restart:
            container.mark_restart(", ".join(restart))
            response["restart"] = container.restart_reasons
        message_back = {
            "feedback": f"Container {container.name} is configured",
            "response": response,
        }
        logger.debug(message_back)
        self.send(text_data=json.dumps(message_back, cls=CustomEncoder))
                

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



