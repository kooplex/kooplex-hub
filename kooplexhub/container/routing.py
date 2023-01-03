from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    re_path(r"hub/ws/container_environment/(?P<userid>\d+)/$", consumers.ContainerConsumer.as_asgi()),
]

