import logging
import time
import uuid

from channels.generic.websocket import AsyncJsonWebsocketConsumer

from .tasks import *#FIXME make explicit!

from .conf import CONTAINER_SETTINGS

logger = logging.getLogger(__name__)


class ContainerLiveConsumer(AsyncJsonWebsocketConsumer):
    """
    Live invalidation feed for container/environment pages.

    This consumer does not perform mutations.
    It only receives server-side live events and forwards them to browsers.
    """

    async def connect(self) -> None:
        self.connection_id = uuid.uuid4().hex[:12]
        self.connected_monotonic = time.monotonic()

        user = self.scope.get("user")
        client = self.scope.get("client")
        path = self.scope.get("path")
        headers = dict(self.scope.get("headers", []))

        logger.info(
            "WS CONNECT requested "
            "id=%s channel=%s client=%s path=%s user=%s "
            "origin=%r user_agent=%r",
            self.connection_id,
            self.channel_name,
            client,
            path,
            getattr(user, "pk", None),
            headers.get(b"origin"),
            headers.get(b"user-agent"),
        )

        if user is None or not user.is_authenticated:
            await self.close(code=4401)
            return

        try:
            self.user = user
            self.user_group_name = self.group_name_for_user(user.pk)
    
            await self.channel_layer.group_add(
                self.user_group_name,
                self.channel_name,
            )
    
            await self.accept()

            logger.info(
                "WS ACCEPTED id=%s channel=%s group=%s",
                self.connection_id,
                self.channel_name,
                self.user_group_name,
            )

        except Exception:
            logger.exception(
                "WS CONNECT FAILED id=%s channel=%s",
                self.connection_id,
                self.channel_name,
            )
            raise

    async def disconnect(self, close_code) -> None:
        lifetime = (
            time.monotonic()
            - getattr(self, "connected_monotonic", time.monotonic())
        )

        logger.warning(
            "WS DISCONNECT "
            "id=%s channel=%s group=%s code=%s lifetime=%.1fs",
            getattr(self, "connection_id", None),
            self.channel_name,
            getattr(self, "user_group_name", None),
            close_code,
            lifetime,
        )
        if hasattr(self, "user_group_name"):
            try:
                await self.channel_layer.group_discard(
                    self.user_group_name,
                    self.channel_name,
                )
            except Exception:
                logger.exception(
                    "WS GROUP DISCARD FAILED "
                    "id=%s channel=%s group=%s",
                    getattr(self, "connection_id", None),
                    self.channel_name,
                    user_group_name,
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
        try:
            logger.debug(
                "WS SEND id=%s channel=%s event=%s",
                getattr(self, "connection_id", None),
                self.channel_name,
                event.get("event"),
            )
            await self.send_json(event["payload"])
        except Exception:
            logger.exception(
                "WS SEND FAILED id=%s channel=%s event=%r",
                getattr(self, "connection_id", None),
                self.channel_name,
                event,
            )
            raise

    @staticmethod
    def group_name_for_user(user_id):
        return f"container-live-user-{user_id}"


