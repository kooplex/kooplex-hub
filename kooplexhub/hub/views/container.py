#FIXME: rename environment
import re
import logging

from django.conf.urls import url
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect
import django_tables2 as tables
from django_tables2 import RequestConfig

from kooplex.lib import standardize_str, custom_redirect

from hub.forms import table_projects
from hub.models import Image
from hub.models import Project, UserProjectBinding
from hub.models import Container, ContainerEnvironment #FIXME: deprecate
from hub.models import ProjectContainerBinding         #FIXME: deprecate
from hub.models import ServiceEnvironment
from hub.models import ProjectServiceEnvironmentBinding

logger = logging.getLogger(__name__)

@login_required
def new(request):
    logger.debug("user %s" % request.user)
    user = request.user
    user_id = request.POST.get('user_id')
    try:
        assert user_id is not None and int(user_id) == user.id, "user id mismatch: %s tries to save %s %s" % (request.user, request.user.id, request.POST.get('user_id'))
        containername = "%s-%s" % (user.username, standardize_str(request.POST.get('name')))
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
def listcontainers(request): #FIXME: rename
    """Renders the containerlist page."""
    logger.debug('Rendering container/list.html')
    #TODO: make volume/image etc changes visible, so the user will know which one needs to be deleted. 
    context_dict = {
        'next_page': 'container:list',
        'menu_container': 'active',
    }
    return render(request, 'container/list.html', context = context_dict)


def showpass(request, container):
    try:
        pw = ContainerEnvironment.objects.get(container = container, name = 'PASSWORD').value
        messages.warning(request, 'Until we find a better way to authorize your access to rstudio server, we created a password for you: %s' % pw)
    except:
        pass

@login_required
def startprojectcontainer(request, project_id, next_page):
    """Starts the project container."""
    user = request.user
    try:
        container = Container.get_userprojectcontainer(user = user, project_id = project_id, create = True)
        container.docker_start()
        showpass(request, container)
    except Container.DoesNotExist:
        messages.error(request, 'Project does not exist')
    except Exception as e:
        logger.error('Cannot start the container %s (project id: %s) -- %s' % (container, project_id, e))
        messages.error(request, 'Cannot start the container -- %s' % e)
    return redirect(next_page)


@login_required
def startcoursecontainer(request, course_id, next_page):
    """Starts the project container."""
    user = request.user
    container = None
    try:
        container = Container.get_usercoursecontainer(user = user, course_id = course_id, create = True)
        container.docker_start()
        showpass(request, container)
    except Container.DoesNotExist:
        messages.error(request, 'Course does not exist')
    except Exception as e:
        logger.error('Cannot start the container %s (course id: %s) -- %s' % (container, course_id, e))
        messages.error(request, 'Cannot start the container -- %s' % e)
    return redirect(next_page)
 

@login_required
def startcontainer(request, container_id, next_page):#FIXME: rename
    """Starts the container."""
    user = request.user
    try:
        environment = ServiceEnvironment.objects.get(user = user, id = container_id)
        environment.start()
        ###showpass(request, container)
    except ServiceEnvironment.DoesNotExist:
        messages.error(request, 'Environment does not exist')
    except Exception as e:
        logger.error(f'Cannot start the environment {environment} -- {e}')
        messages.error(request, f'Cannot start environment {e}')
    return redirect(next_page)


@login_required
def opencontainer(request, container_id, next_page):#FIXME: rename
    """Opens a container"""
    user = request.user
    try:
        environment = ServiceEnvironment.objects.get(id = container_id, user = user, state = Container.ST_RUNNING)
        environment.wait_until_ready()
        return custom_redirect(environment.url_public, token = environment.user.profile.token)
    except Container.DoesNotExist:
        messages.error(request, 'Container is missing or stopped')
    return redirect(next_page)


@login_required
def stopcontainer(request, container_id, next_page):#FIXME: rename
    """Stops a container"""
    user = request.user
    try:
        environment = ServiceEnvironment.objects.get(user = user, id = container_id)
        environment.stop()
    except ServiceEnvironment.DoesNotExist:
        messages.error(request, 'Environment does not exist')
    except Exception as e:
        logger.error(f'Cannot stop the environment {environment} -- {e}')
        messages.error(request, f'Cannot stop environment {e}')
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
            'next_page': 'container:list',
        }
        return render(request, 'container/manage.html', context = context_dict)
    else:
        container.image = Image.objects.get(id = request.POST.get('container_image_id'))
        container.save()
        project_ids_before = set(request.POST.getlist('project_ids_before'))
        project_ids_after = set(request.POST.getlist('project_ids_after'))
        oops = 0
        added = []
        for project_id in project_ids_after.difference(project_ids_before):
            try:
                project = Project.get_userproject(project_id = project_id, user = user)
                ProjectContainerBinding.objects.create(container = container, project = project)
                added.append(str(project))
                logger.debug('added project %s to container %s' % (project, container))
            except Exception as e:
                logger.error('not authorized to add project_id %s to container %s -- %s' % (project_id, container, e))
                oops += 1
        removed = []
        for project_id in project_ids_before.difference(project_ids_after):
            try:
                project = Project.get_userproject(project_id = project_id, user = user)
                ProjectContainerBinding.objects.get(container = container, project = project).delete()
                removed.append(str(project))
                logger.debug('removed project %s from container %s' % (project, container))
            except Exception as e:
                logger.error('not authorized to remove project_id %s from container %s -- %s' % (project_id, container, e))
                oops += 1
        if len(added):
            messages.info(request, 'Added projects %s to container %s' % (",".join(added), container))
        if len(removed):
            messages.info(request, 'Removed projects %s from container %s' % (",".join(removed), container))
        if oops:
            messages.warning(request, 'Some problems (%d) occured during handling yout request.' % (oops))
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
    url(r'^startcourse/(?P<course_id>\d+)/(?P<next_page>\w+:?\w*)$', startcoursecontainer, name = 'startcoursecontainer'),
]
