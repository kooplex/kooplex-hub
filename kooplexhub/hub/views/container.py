import re
import logging

from django.conf.urls import url
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect

from hub.models import Project
from hub.models import Container

logger = logging.getLogger(__name__)

@login_required
def startprojectcontainer(request, project_id, next_page):
    """Starts the project container."""
    user = request.user
    try:
        container = Container.get_userprojectcontainer(user = user, project_id = project_id, create = True)
        container.docker_start()
    except Container.DoesNotExist:
        messages.error(request, 'Project does not exist')
    except Exception as e:
        messages.error(request, 'Cannot start the container -- %s' % e)
        raise
    return redirect(next_page)

@login_required
def startcontainer(request, container_id, next_page):
    """Starts the container."""
    user = request.user
    try:
        container = Container.objects.get(user = user, id = container_id)
        container.docker_start()
    except Container.DoesNotExist:
        messages.error(request, 'Container does not exist')
    except Exception as e:
        messages.error(request, 'Cannot start the container -- %s' % e)
        raise
    return redirect(next_page)

@login_required
def opencontainer(request, container_id, next_page):
    """Opens a container"""
    user = request.user
    try:
        container = Container.get_usercontainer(container_id = container_id, user = user, is_running = True)
        container.wait_until_ready()
        return redirect(container.url_external)
    except Container.DoesNotExist:
        messages.error(request, 'Container is missing or stopped')
    #except ConnectionError:
    #    messages.error(request, 'Could not open it. Try again, please! If you keep seeing this error then ask an administrator <strong> %s </strong>'%get_settings('hub', 'adminemail'))
    return redirect(next_page)

@login_required
def stopcontainer(request, container_id, next_page):
    """Stops a container"""
    user = request.user
    logger.error(next_page)
    try:
        container = Container.get_usercontainer(container_id = container_id, user = user, is_running = True)
        container.docker_stop(remove = False)
    except Container.DoesNotExist:
        messages.error(request, 'Container is missing or stopped')
    return redirect(next_page)


@login_required
def removecontainer(request, container_id, next_page):
    """Stops a container"""
    user = request.user
    try:
        container = Container.get_usercontainer(container_id = container_id, user = user)
        container.docker_stop(remove = True)
    except Container.DoesNotExist:
        messages.error(request, 'Container is missing or stopped')
    return redirect(next_page)


urlpatterns = [
    url(r'startproject/(?P<project_id>\d+)/(?P<next_page>\w+:?\w*)$', startprojectcontainer, name = 'startprojectcontainer'),
    url(r'start/(?P<container_id>\d+)/(?P<next_page>\w+:?\w*)$', startcontainer, name = 'start'),
    url(r'open/(?P<container_id>\d+)/(?P<next_page>\w+:?\w*)$', opencontainer, name = 'open'),
    url(r'stop/(?P<container_id>\d+)/(?P<next_page>\w+:?\w*)$', stopcontainer, name = 'stop'),
    url(r'remove/(?P<container_id>\d+)/(?P<next_page>\w+:?\w*)$', removecontainer, name = 'remove'),
]
