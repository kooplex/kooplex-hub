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

import container.routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kooplexhub.settings')

#application = get_asgi_application()
app = get_asgi_application()

application = ProtocolTypeRouter({
    "http": app,
    "websocket": AllowedHostsOriginValidator(
            AuthMiddlewareStack(URLRouter(container.routing.websocket_urlpatterns))
        ),
})
