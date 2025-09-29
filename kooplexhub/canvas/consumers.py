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

from .models import Canvas, CanvasCourse

from hub.util import SyncSkeleton

from .conf import CANVAS_SETTINGS

logger = logging.getLogger(__name__)


class CanvasGetCoursesConsumer(SyncSkeleton):
    def receive(self, text_data):
        parsed = json.loads(text_data)
        logger.debug(parsed)
        request = parsed.get('request')
        response = {
            'response': request,
        }
        try:
            canvas = Canvas.objects.get(user__id = self.userid)
            created_ids=list(map(lambda o: o.canvas_course_id, CanvasCourse.objects.all()))
            canvas_courses = filter(lambda x: x['id'] not in created_ids, canvas.get_courses())
            f=CANVAS_SETTINGS['filter']
            if old_filter:
                canvas_courses=list(filter(f, canvas_courses))
            response.update({
                "feedback": "Your canvas course list is refreshed", 
                "replace_widgets": { '[id=canvasSelection]': render_to_string("widgets/list_canvascourses.html", {"canvascourses":  canvas_courses }) },
            })
        except Exception as e:
            response.update({
                "feedback": f"Failed to fetch canvas course list", 
                "error": f"problem loading canvas resources -- {e}",
            })
        self.send(text_data = json.dumps(response))


