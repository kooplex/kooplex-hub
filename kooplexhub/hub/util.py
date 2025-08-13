import logging
from channels.generic.websocket import WebsocketConsumer
from channels.generic.websocket import AsyncWebsocketConsumer
from django.core.exceptions import FieldDoesNotExist
from django.template.loader import render_to_string
import json

logger = logging.getLogger(__name__)


class Config:
    @staticmethod
    def is_model_field(instance, attr_name):
        # Get the class of the instance
        cls = instance.__class__
        # Check if the attribute is a Django model field
        try:
            instance._meta.get_field(attr_name)
            return True
        except FieldDoesNotExist:
            pass
        return False

    def _msg(self, instance, message, errors={}, reload=False):
        template_kwargs=getattr(self, 'template_kwargs', {})
        template_kwargs.update({
            self.instance_reference: instance,
            "errors": errors,
            })
        message_back = {
            f"{self.instance_reference}_id": instance.id,
            "feedback": message,
            "response": "reloadpage" if reload else render_to_string(self.template, template_kwargs),
        }
        logger.debug(message_back["feedback"])
        self.send(text_data=json.dumps(message_back))

    def _chg_image(self, instance, image, attribute='image'):
        old_value=getattr(instance, attribute).name
        setattr(instance, attribute, image)
        instance.save()
        m=f"The {attribute} of {self.instance_reference} {instance.name} changed from {old_value} to {image.name}"
        self._msg(instance, m)

    def _chg_bindings(self, instance, ids, obj_type, bind_type, attr, m):
        a=[]
        r=[]
        for o in obj_type.objects.filter(id__in = ids):
            b, _=bind_type.objects.get_or_create(**{attr: o, self.instance_reference: instance})
            a.append(getattr(b, attr).name)
        for b in bind_type.objects.filter(**{self.instance_reference: instance}).exclude(**{f"{attr}__id__in": ids}):
            r.append(getattr(b, attr).name)
            b.delete()
        if a:
            m += "added " + ", ".join(a) + "\n"
        if r:
            m += "removed " + ", ".join(r) + "\n"
        if a or r:
            self._msg(instance, m)


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
    def get_userid(self):
        return self.userid


class  AsyncSkeleton(AsyncWebsocketConsumer):
    async def connect(self):
        if not self.scope['user'].is_authenticated:
            return
        self.userid = int(self.scope["url_route"]["kwargs"].get('userid'))
        if self.scope['user'].id != self.userid: #not authorized
            return
        assert hasattr(self, 'identifier_'), "Make sure child class implements self.identifier:str"
        self.identifier=f"{self.identifier_}-{self.userid}"
        await self.channel_layer.group_add(self.identifier, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        self.userid = int(self.scope["url_route"]["kwargs"].get('userid'))
        self.identifier=f"{self.identifier_}-{self.userid}"
        await self.channel_layer.group_discard(self.identifier, self.channel_name)

    async def feedback(self, event):
        # Send message to WebSocket
        await self.send(text_data=json.dumps(event))
