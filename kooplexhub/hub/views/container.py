import re
import logging

from django.conf.urls import url
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect

#from hub.forms import FormContainer
from hub.models import Project
from hub.models import Container
from hub.models import ProjectContainerBinding

logger = logging.getLogger(__name__)

@login_required
def new(request):
    logger.debug("user %s" % request.user)
    user = request.user
    user_id = request.POST.get('user_id')
    try:
        assert user_id is not None and int(user_id) == user.id, "user id mismatch: %s tries to save %s %s" % (request.user, request.user.id, request.POST.get('user_id'))
        containername = "%s-%s" % (request.POST.get('name'), user.username)
        for container in user.profile.containers:
            assert container.name != containername, "Not a unique name"
        Container.objects.create(user = user, name = containername)
        messages.info(request, 'Your new container is created with name %s' % containername)
        return redirect('container:list')
    except Exception as e:
        logger.error("New container not created -- %s" % e)
        messages.error(request, 'Creation of a new container is refused.')
        return redirect('indexpage')
        

@login_required
def listcontainers(request):
    """Renders the containerlist page."""
    logger.debug('Rendering container/list.html')
    context_dict = {
        'next_page': 'container:list',
    }
    return render(request, 'container/list.html', context = context_dict)


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
    return redirect(next_page)


@login_required
def opencontainer(request, container_id, next_page):
    """Opens a container"""
    user = request.user
    try:
        container = Container.get_usercontainer(container_id = container_id, user = user, state = Container.ST_RUNNING)
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
    try:
        container = Container.get_usercontainer(container_id = container_id, user = user, state = Container.ST_RUNNING)
        container.docker_stop()
    except Container.DoesNotExist:
        messages.error(request, 'Container is missing or stopped')
    return redirect(next_page)


@login_required
def removecontainer(request, container_id, next_page):
    """Removes a container"""
    user = request.user
    try:
        container = Container.get_usercontainer(container_id = container_id, user = user)
        container.docker_remove()
    except Container.DoesNotExist:
        messages.error(request, 'Container is missing or stopped')
    return redirect(next_page)


@login_required
def destroycontainer(request, container_id, next_page):
    """Deletes a container instance"""
    user = request.user
    try:
        container = Container.get_usercontainer(container_id = container_id, user = user)
        container.docker_remove()
        container.delete()
    except Container.DoesNotExist:
        messages.error(request, 'Container is missing or stopped')
    return redirect(next_page)


@login_required
def addproject(request, container_id):
    """Manage your projects"""
    def nocontainer(upb):
        img = upb.project.image
        return img is None or img == container.image

    next_page = 'container:list'
    user = request.user
    logger.debug("user %s method %s" % (user, request.method))
    try:
        container = Container.get_usercontainer(container_id = container_id, user = user)
    except Container.DoesNotExist:
        messages.error(request, 'Container is missing or stopped')
        return redirect(next_page)
    if request.method == 'GET':
        context_dict = {
            'container': container,
        }
        return render(request, 'container/manage.html', context = context_dict)
    else:
        project_ids = request.POST.getlist('project_ids')
        for p in container.projects:
            if p.id in project_ids:
                project_ids.remove(p.id)
            else:
                project = Project.objects.get(id = p.id)
                ProjectContainerBinding.objects.get(container = container, project = project).delete()
        while len(project_ids):
            pid = project_ids.pop()
            project = Project.get_userproject(id = pid, user = user)
            ProjectContainerBinding.objects.create(container = container, project = project)
        return redirect(next_page)


urlpatterns = [
    url(r'^new/?$', new, name = 'new'), 
    url(r'^list/?$', listcontainers, name = 'list'), 
    url(r'^start/(?P<container_id>\d+)/(?P<next_page>\w+:?\w*)$', startcontainer, name = 'start'),
    url(r'^open/(?P<container_id>\d+)/(?P<next_page>\w+:?\w*)$', opencontainer, name = 'open'),
    url(r'^stop/(?P<container_id>\d+)/(?P<next_page>\w+:?\w*)$', stopcontainer, name = 'stop'),
    url(r'^remove/(?P<container_id>\d+)/(?P<next_page>\w+:?\w*)$', removecontainer, name = 'remove'),
    url(r'^destroy/(?P<container_id>\d+)/(?P<next_page>\w+:?\w*)$', destroycontainer, name = 'destroy'),

    url(r'^addproject/(?P<container_id>\d+)$', addproject, name = 'addproject'),
    url(r'^startproject/(?P<project_id>\d+)/(?P<next_page>\w+:?\w*)$', startprojectcontainer, name = 'startprojectcontainer'),
]
