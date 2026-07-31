import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

import container.routing

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "kooplex.settings")

django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AuthMiddlewareStack(
            URLRouter(
                container.routing.websocket_urlpatterns,
            )
        ),
    }
)

##
##"""
##ASGI config for kooplexhub project.
##
##It exposes the ASGI callable as a module-level variable named ``application``.
##
##For more information on this file, see
##https://docs.djangoproject.com/en/3.2/howto/deployment/asgi/
##"""
##
##import os
##
###websocket
##from channels.auth import AuthMiddlewareStack
##from channels.routing import ProtocolTypeRouter, URLRouter
##from channels.security.websocket import AllowedHostsOriginValidator
##from django.core.asgi import get_asgi_application
##from django.urls import re_path, path
##
##from hub.consumers import TokenConfigurator, ResourceConsumer
##from container.consumers import ContainerLiveConsumer, ContainerFetchlogConsumer, ContainerControlConsumer, MonitorConsumer
##from volume.consumers import VolumeConfigConsumer
##from project.consumers import JoinProjectConsumer, ProjectConfigConsumer, ProjectGetContainersConsumer, UserHandler as ProjectUserHandler
##from education.consumers import CourseGetContainersConsumer, CourseConfigConsumer, HandinConsumer, AssignmentConsumer, AssignmentScoreConsumer, UserHandler as CourseUserHandler
##from canvas.consumers import CanvasGetCoursesConsumer
##
##os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kooplexhub.settings')
##
###application = get_asgi_application()
##app = get_asgi_application()
##
##application = ProtocolTypeRouter({
##    "http": app,
##    "websocket": AllowedHostsOriginValidator(
##        AuthMiddlewareStack(
##            URLRouter([
##                re_path(r"ws/tokens/(?P<userid>\d+)/$", TokenConfigurator.as_asgi()),
##                re_path(r"ws/resources/$", ResourceConsumer.as_asgi()),
##                re_path(r"ws/container/live/(?P<userid>\d+)/$", ContainerLiveConsumer.as_asgi()),
##
##                re_path(r"ws/container/fetchlog/(?P<userid>\d+)/$", ContainerFetchlogConsumer.as_asgi()),
##                re_path(r"ws/container/control/(?P<userid>\d+)/$", ContainerControlConsumer.as_asgi()),
##                re_path(r"ws/volume/config/(?P<userid>\d+)/$", VolumeConfigConsumer.as_asgi()),
##                re_path(r"ws/monitor/node/(?P<userid>\d+)/$", MonitorConsumer.as_asgi()),
##                re_path(r"ws/project/config/(?P<userid>\d+)/$", ProjectConfigConsumer.as_asgi()),
##                re_path(r"ws/project/userhandler/(?P<userid>\d+)/$", ProjectUserHandler.as_asgi()),
##                re_path(r"ws/project/join/(?P<userid>\d+)/$", JoinProjectConsumer.as_asgi()),
##                re_path(r"ws/project/container/(?P<userid>\d+)/$", ProjectGetContainersConsumer.as_asgi()),
##                re_path(r"ws/course/config/(?P<userid>\d+)/$", CourseConfigConsumer.as_asgi()),
##                re_path(r"ws/course/userhandler/(?P<userid>\d+)/$", CourseUserHandler.as_asgi()),
##                re_path(r"ws/education/container/(?P<userid>\d+)/$", CourseGetContainersConsumer.as_asgi()),
##                re_path(r"ws/education/handin/(?P<userid>\d+)/$", HandinConsumer.as_asgi()),
##                re_path(r"ws/assignment/(?P<userid>\d+)/$", AssignmentConsumer.as_asgi()),
##                re_path(r"ws/score/(?P<userid>\d+)/$", AssignmentScoreConsumer.as_asgi()),
###                re_path(r"ws/assignment_summary/(?P<userid>\d+)/$", AssignmentSummaryConsumer.as_asgi()),
##                re_path(r"ws/canvas/fetchcourses/(?P<userid>\d+)/$", CanvasGetCoursesConsumer.as_asgi()),
##            ])
##        )
##    ),
##})
