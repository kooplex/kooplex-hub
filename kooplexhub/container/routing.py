from django.urls import re_path

from .consumers import ContainerLiveConsumer

websocket_urlpatterns = [
    re_path(
        r"^ws/container/live/$",
        ContainerLiveConsumer.as_asgi(),
    ),
]
