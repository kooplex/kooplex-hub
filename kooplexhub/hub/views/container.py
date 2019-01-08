import re
import logging

from django.conf.urls import url
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect
import django_tables2 as tables
from django_tables2 import RequestConfig

from kooplex.lib import standardize_str

from hub.forms import table_projects
from hub.models import Image
from hub.models import Project, UserProjectBinding
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
        containername = "%s-%s" % (standardize_str(request.POST.get('name')), user.username)
        for container in user.profile.containers:
            assert container.name != containername, "Not a unique name"
        logger.debug("name is okay: %s" % containername)
        image = Image.objects.get(id = request.POST.get('image'))
        Container.objects.create(user = user, name = containername, image = image)
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
        logger.error('Cannot start the container %s (project id: %s) -- %s' % (container, project_id, e))
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
        logger.error('Cannot start the container %s -- %s' % (container, e))
        messages.error(request, 'Cannot start the container -- %s' % e)
    return redirect(next_page)


@login_required
def opencontainer(request, container_id, next_page):
    """Opens a container"""
    user = request.user
    try:
        container = Container.objects.get(id = container_id, user = user, state = Container.ST_RUNNING)
        container.wait_until_ready()
        return redirect(container.url_external)
    except Container.DoesNotExist:
        messages.error(request, 'Container is missing or stopped')
    return redirect(next_page)


@login_required
def stopcontainer(request, container_id, next_page):
    """Stops a container"""
    user = request.user
    try:
        container = Container.objects.get(id = container_id, user = user, state = Container.ST_RUNNING)
        container.docker_stop()
    except Container.DoesNotExist:
        messages.error(request, 'Container is missing or stopped')
    return redirect(next_page)


@login_required
def removecontainer(request, container_id, next_page):
    """Removes a container"""
    user = request.user
    try:
        container = Container.objects.get(id = container_id, user = user)
        container.docker_remove()
    except Container.DoesNotExist:
        messages.error(request, 'Container is missing or stopped')
    return redirect(next_page)


@login_required
def destroycontainer(request, container_id, next_page):
    """Deletes a container instance"""
    user = request.user
    try:
        container = Container.objects.get(id = container_id, user = user)
        container.docker_remove()
        container.delete()
    except Container.DoesNotExist:
        messages.error(request, 'Container is missing or stopped')
        raise
    return redirect(next_page)


@login_required
def addproject(request, container_id):
    """Manage your projects"""
    next_page = 'container:list'
    user = request.user
    logger.debug("user %s method %s" % (user, request.method))
    try:
        container = Container.objects.get(id = container_id, user = user)
    except Container.DoesNotExist:
        messages.error(request, 'Container is missing or stopped')
        return redirect(next_page)
    if request.method == 'GET':
        table = table_projects(container)
        table_project = table(UserProjectBinding.objects.filter(user = user))
        RequestConfig(request).configure(table_project)
        context_dict = {
            'images': Image.objects.all(),
            'container': container,
            't_projects': table_project,
        }
        return render(request, 'container/manage.html', context = context_dict)
    else:
        container.image = Image.objects.get(id = request.POST.get('container_image_id'))
        container.save()
        project_ids = request.POST.getlist('project_ids')
        for p in container.projects:
            if p.id in project_ids:
                project_ids.remove(p.id)
            else:
                project = Project.objects.get(id = p.id)
                ProjectContainerBinding.objects.get(container = container, project = project).delete()
        while len(project_ids):
            pid = project_ids.pop()
            project = Project.get_userproject(project_id = pid, user = user)
            ProjectContainerBinding.objects.create(container = container, project = project)
        return redirect(next_page)


@login_required
def refreshlogs(request, container_id):
    container = Container.objects.get(id = container_id)
    container.refresh_state()
    return redirect('container:list')

urlpatterns = [
    url(r'^new/?$', new, name = 'new'), 
    url(r'^list/?$', listcontainers, name = 'list'), 
    url(r'^start/(?P<container_id>\d+)/(?P<next_page>\w+:?\w*)$', startcontainer, name = 'start'),
    url(r'^open/(?P<container_id>\d+)/(?P<next_page>\w+:?\w*)$', opencontainer, name = 'open'),
    url(r'^stop/(?P<container_id>\d+)/(?P<next_page>\w+:?\w*)$', stopcontainer, name = 'stop'),
    url(r'^remove/(?P<container_id>\d+)/(?P<next_page>\w+:?\w*)$', removecontainer, name = 'remove'),
    url(r'^destroy/(?P<container_id>\d+)/(?P<next_page>\w+:?\w*)$', destroycontainer, name = 'destroy'),
    url(r'^refreshlogs/(?P<container_id>\d+)$', refreshlogs, name = 'refreshlogs'),

    url(r'^addproject/(?P<container_id>\d+)$', addproject, name = 'addproject'),
    url(r'^startproject/(?P<project_id>\d+)/(?P<next_page>\w+:?\w*)$', startprojectcontainer, name = 'startprojectcontainer'),
]
