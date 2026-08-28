from django.urls import path

from .conf import HUB_SETTINGS
from .consumers import LiveConsumer


websocket_urlpatterns = [
    path(
        HUB_SETTINGS.live.path,
        LiveConsumer.as_asgi(),
    ),
]

