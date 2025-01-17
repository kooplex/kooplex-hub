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

from container.forms import FormContainer
from django.template.loader import render_to_string

from .models import Canvas

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

class CanvasGetCoursesConsumer(SyncSkeleton):
    def receive(self, text_data):
        canvas = Canvas.objects.get(user__id = self.userid)
        resp = {
            "feedback": "Your canvas course list is refreshed", 
            "response": render_to_string("widgets/list_canvascourses.html", { "canvascourses": canvas.get_courses() }) , #FIXME: filter old/filter present
            "echo": canvas.get_courses() , #FIXME: filter old/filter present
        }
        self.send(text_data = json.dumps(resp))


