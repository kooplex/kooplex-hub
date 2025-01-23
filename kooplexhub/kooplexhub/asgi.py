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
from django.urls import re_path, path

from container.consumers import ContainerFetchlogConsumer, ContainerControlConsumer, ContainerConfigConsumer, MonitorConsumer
from project.consumers import ProjectGetJoinableConsumer, JoinProjectConsumer, ProjectConfigConsumer, ProjectGetContainersConsumer
from education.consumers import CourseGetContainersConsumer, CourseConfigConsumer, HandinConsumer#, AssignmentConsumer, AssignmentSummaryConsumer, 
from canvas.consumers import CanvasGetCoursesConsumer

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kooplexhub.settings')

#application = get_asgi_application()
app = get_asgi_application()

application = ProtocolTypeRouter({
    "http": app,
    "websocket": AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter([
                re_path(r"hub/ws/container/fetchlog/(?P<userid>\d+)/$", ContainerFetchlogConsumer.as_asgi()),
                re_path(r"hub/ws/container/control/(?P<userid>\d+)/$", ContainerControlConsumer.as_asgi()),
                re_path(r"hub/ws/container/config/(?P<userid>\d+)/$", ContainerConfigConsumer.as_asgi()),
                re_path(r"hub/ws/monitor/node/(?P<userid>\d+)/$", MonitorConsumer.as_asgi()),
                re_path(r"hub/ws/project/config/(?P<userid>\d+)/$", ProjectConfigConsumer.as_asgi()),
                re_path(r"hub/ws/project/fetchjoinable/(?P<userid>\d+)/$", ProjectGetJoinableConsumer.as_asgi()),
                re_path(r"hub/ws/project/join/(?P<userid>\d+)/$", JoinProjectConsumer.as_asgi()),
                re_path(r"hub/ws/project/container/(?P<userid>\d+)/$", ProjectGetContainersConsumer.as_asgi()),
                re_path(r"hub/ws/course/config/(?P<userid>\d+)/$", CourseConfigConsumer.as_asgi()),
                re_path(r"hub/ws/education/container/(?P<userid>\d+)/$", CourseGetContainersConsumer.as_asgi()),
                re_path(r"hub/ws/education/handin/(?P<userid>\d+)/$", HandinConsumer.as_asgi()),
#                re_path(r"hub/ws/education/(?P<userid>\d+)/$", AssignmentConsumer.as_asgi()),
#                re_path(r"hub/ws/assignment_summary/(?P<userid>\d+)/$", AssignmentSummaryConsumer.as_asgi()),
                re_path(r"hub/ws/canvas/fetchcourses/(?P<userid>\d+)/$", CanvasGetCoursesConsumer.as_asgi()),
            ])
        )
    ),
})
