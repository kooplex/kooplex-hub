from django.urls import re_path

from .consumers import LiveConsumer


websocket_urlpatterns = [
    re_path(
        r"^ws/live/$",
        LiveConsumer.as_asgi(),
    ),
]

