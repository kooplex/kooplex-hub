import logging

from channels.generic.websocket import AsyncJsonWebsocketConsumer

from .tasks import *

from .conf import CONTAINER_SETTINGS

logger = logging.getLogger(__name__)





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


