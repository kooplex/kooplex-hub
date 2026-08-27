import logging
import time
import uuid

from channels.generic.websocket import (
    AsyncJsonWebsocketConsumer,
)

from .services.live import live_group_for_user


logger = logging.getLogger(__name__)


class LiveConsumer(
    AsyncJsonWebsocketConsumer
):
    async def connect(self):
        self.connection_id = (
            uuid.uuid4().hex[:12]
        )
        self.connected_monotonic = (
            time.monotonic()
        )

        user = self.scope.get("user")

        if (
            user is None
            or not user.is_authenticated
        ):
            await self.close(code=4401)
            return

        self.user = user

        self.user_group_name = (
            live_group_for_user(user.pk)
        )

        await self.channel_layer.group_add(
            self.user_group_name,
            self.channel_name,
        )

        await self.accept()

        logger.debug(
            "Live WS connected user=%s id=%s",
            user.pk,
            self.connection_id,
        )

    async def disconnect(self, close_code):
        if hasattr(
            self,
            "user_group_name",
        ):
            await self.channel_layer.group_discard(
                self.user_group_name,
                self.channel_name,
            )

        logger.debug(
            "Live WS disconnected id=%s code=%s",
            getattr(
                self,
                "connection_id",
                None,
            ),
            close_code,
        )

    async def receive_json(
        self,
        content,
        **kwargs,
    ):
        # Server-push only for now.
        return

    async def live_event(self, event):
        await self.send_json(
            event["payload"]
        )


