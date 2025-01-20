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

from hub.util import SyncSkeleton

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




class CanvasGetCoursesConsumer(SyncSkeleton):
    def receive(self, text_data):
        canvas = Canvas.objects.get(user__id = self.userid)
        canvas_courses = canvas.get_courses()
        #FIXME: filter what is present
        ######################
        resp = {
            "feedback": "Your canvas course list is refreshed", 
            "response": render_to_string("widgets/list_canvascourses.html", {"canvascourses":  canvas_courses, "maxheight": "200px" }),
        }
        self.send(text_data = json.dumps(resp))


