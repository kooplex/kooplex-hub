"""
ASGI config for kooplexhub project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/howto/deployment/asgi/
"""

import os

#websocket
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application
from django.urls import re_path

from container.consumers import ContainerConsumer
from project.consumers import ProjectConsumer

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kooplexhub.settings')

#application = get_asgi_application()
app = get_asgi_application()

application = ProtocolTypeRouter({
    "http": app,
    "websocket": AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter([
                re_path(r"hub/ws/container_environment/(?P<userid>\d+)/$", ContainerConsumer.as_asgi()),
                re_path(r"hub/ws/project/(?P<userid>\d+)/$", ProjectConsumer.as_asgi()),
            ])
        )
    ),
})
