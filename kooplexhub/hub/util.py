import logging
from channels.generic.websocket import WebsocketConsumer
from channels.generic.websocket import AsyncWebsocketConsumer
from django.core.exceptions import FieldDoesNotExist
from django.template.loader import render_to_string
import json

logger = logging.getLogger(__name__)

def normalize_pk(value):
    if value in (None, '', 'None'):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


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
