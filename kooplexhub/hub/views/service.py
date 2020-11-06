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
from hub.forms import table_fslibrary
from hub.models import Image
from hub.models import Project, UserProjectBinding
from hub.models import Service
from hub.models import ProjectServiceBinding
from hub.models import FSLibrary, FSLibraryServiceBinding

logger = logging.getLogger(__name__)

@login_required
def new(request):
    logger.debug("user %s" % request.user)
    user = request.user
    user_id = request.POST.get('user_id')
    try:
        assert user_id is not None and int(user_id) == user.id, "user id mismatch: %s tries to save %s %s" % (request.user, request.user.id, request.POST.get('user_id'))
        servicename = "%s-%s" % (user.username, standardize_str(request.POST.get('name')))
        image = Image.objects.get(id = request.POST.get('image'))
        env, created = Service.objects.get_or_create(user = user, name = servicename, image = image)
        assert created, "Service environment with name %s is not unique" % servicename
        messages.info(request, 'Your new service environment is created with name %s' % servicename)
    except Exception as e:
        logger.error("New container not created -- %s" % e)
        messages.error(request, 'Service environment is not created: %s' % e)
    return redirect('service:list')
        

@login_required
def listservices(request):
    """Renders the containerlist page."""
    logger.debug('Rendering container/list.html')
    #TODO: make volume/image etc changes visible, so the user will know which one needs to be deleted. 
    context_dict = {
        'next_page': 'service:list',
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
def startservice(request, environment_id, next_page):
    """Starts the container."""
    user = request.user
    try:
        svc = Service.objects.get(user = user, id = environment_id)
        svc.start()
    except Service.DoesNotExist:
        messages.error(request, 'Service environment does not exist')
    except Exception as e:
        logger.error(f'Cannot start the environment {svc} -- {e}')
        messages.error(request, f'Cannot start service environment {e}')
    return redirect(next_page)


@login_required
def openservice(request, environment_id, next_page):
    """Opens a container"""
    user = request.user
    try:
        environment = Service.objects.get(id = environment_id, user = user)
        if environment.state in [ Service.ST_RUNNING, Service.ST_NEED_RESTART ]:
            environment.wait_until_ready()
            return custom_redirect(environment.url_public, token = environment.user.profile.token)
        else:
            messages.error(request, f'Cannot open {environment.name} of state {environment.state}')
    except Service.DoesNotExist:
        messages.error(request, 'Environment is missing')
    return redirect(next_page)


@login_required
def stopservice(request, environment_id, next_page):
    """Stops a container"""
    user = request.user
    try:
        svc = Service.objects.get(user = user, id = environment_id)
        svc.stop()
    except Service.DoesNotExist:
        messages.error(request, 'Environment does not exist')
    except Exception as e:
        logger.error(f'Cannot stop the environment {svc} -- {e}')
        messages.error(request, f'Cannot stop environment {e}')
    return redirect(next_page)


@login_required
def destroyservice(request, environment_id, next_page):
    """Deletes a container instance"""
    user = request.user
    try:
        svc = Service.objects.get(id = environment_id, user = user)
        svc.stop()
        svc.delete()
    except Service.DoesNotExist:
        messages.error(request, 'Service environment does not exist')
        raise
    return redirect(next_page)


@login_required
def configureservice(request, environment_id):
    """Manage your projects"""
    next_page = 'service:list'
    user = request.user
    logger.debug("user %s method %s" % (user, request.method))
    try:
        svc = Service.objects.get(id = environment_id, user = user)
    except Service.DoesNotExist:
        messages.error(request, 'Service environment does not exist')
        return redirect(next_page)
    if request.method == 'GET':
        table = table_projects(svc)
        #TODO: search fields
        table_project = table(UserProjectBinding.objects.filter(user = user))
        RequestConfig(request).configure(table_project)

        table = table_fslibrary(svc)
        #FIXME: pattern = request.POST.get('library', '')
        #FIXME: table_synclibs = t(FSLibrary.objects.filter(token__user = user)) if pattern == '' else t(FSLibrary.objects.filter(token__user = user, library_name__icontains = pattern))
        table_synclibs = table(FSLibrary.objects.filter(token__user = user).exclude(sync_folder__exact = ''))
        RequestConfig(request).configure(table_synclibs)

        context_dict = {
            'images': Image.objects.all(),
            'container': svc,
            't_projects': table_project,
            't_synclibs': table_synclibs,
            'next_page': 'service:list',
        }
        return render(request, 'container/manage.html', context = context_dict)
    else:
        is_running = svc.state == svc.ST_RUNNING

        image_before = svc.image
        image_after = Image.objects.get(id = request.POST.get('container_image_id'))
        svc.image = image_after
        if is_running and image_after != image_before:
            svc.state = svc.ST_NEED_RESTART

        project_ids_before = set(request.POST.getlist('project_ids_before'))
        project_ids_after = set(request.POST.getlist('project_ids_after'))
        oops = 0
        added = []
        for project_id in project_ids_after.difference(project_ids_before):
            try:
                project = Project.get_userproject(project_id = project_id, user = user)
                ProjectServiceBinding.objects.create(service = svc, project = project)
                added.append(f'project {project.name}')
                logger.debug('added project %s to container %s' % (project, svc))
            except Exception as e:
                logger.error('not authorized to add project_id %s to container %s -- %s' % (project_id, svc, e))
                oops += 1
        removed = []
        for project_id in project_ids_before.difference(project_ids_after):
            try:
                project = Project.get_userproject(project_id = project_id, user = user)
                ProjectServiceBinding.objects.get(service = svc, project = project).delete()
                removed.append(f'project {project.name}')
                logger.debug('removed project %s from container %s' % (project, svc))
            except Exception as e:
                logger.error('not authorized to remove project_id %s from container %s -- %s' % (project_id, svc, e))
                oops += 1

        for id_create in request.POST.getlist('fsl_ids'):
            fsl = FSLibrary.objects.get(id = id_create)
            if fsl.token.user != user:
                logger.error("Unauthorized request fsl: %s, user: %s" % (fsl, user))
                oops += 1
                continue
            FSLibraryServiceBinding.objects.create(service = svc, fslibrary = fsl)
            added.append(f'synchron library {fsl.library_name}')
        for id_remove in set(request.POST.getlist('fslpb_ids_before')).difference(set(request.POST.getlist('fslpb_ids_after'))):
            try:
                fslsb = FSLibraryServiceBinding.objects.get(id = id_remove, service = svc)
                if fslsb.fslibrary.token.user != user:
                    logger.error("Unauthorized request fsl: %s, user: %s" % (fsl, user))
                    oops += 1
                    continue
                removed.append(f'synchron library {fsl.library_name}')
                fslsb.delete()
            except FSLibraryServiceBinding.DoesNotExist:
                logger.error("Is %s hacking" % user)
                oops += 1

        if len(added):
            if is_running:
                svc.state = svc.ST_NEED_RESTART
            messages.info(request, 'Added %s to service environment %s' % (",".join(added), svc))
        if len(removed):
            if is_running:
                svc.state = svc.ST_NEED_RESTART
            messages.info(request, 'Removed %s from service environmtn %s' % (",".join(removed), svc))
        if oops:
            messages.warning(request, 'Some problems (%d) occured during handling yout request.' % (oops))

        svc.save()
        return redirect(next_page)


@login_required
def refreshlogs(request, environment_id):
    user = request.user
    try:
        svc = Service.objects.get(user = user, id = environment_id)
        svc.refresh_state()
    except Service.DoesNotExist:
        messages.error(request, 'Environment does not exist')
    except Exception as e:
        logger.error(f'Cannot refresh service environment information {svc} -- {e}')
        messages.error(request, f'Cannot refresh service environment information {svc}')
    return redirect('service:list')

urlpatterns = [
    url(r'^new/?$', new, name = 'new'), 
    url(r'^list/?$', listservices, name = 'list'), 
    url(r'^start/(?P<environment_id>\d+)/(?P<next_page>\w+:?\w*)$', startservice, name = 'start'),
    url(r'^open/(?P<environment_id>\d+)/(?P<next_page>\w+:?\w*)$', openservice, name = 'open'),
    url(r'^stop/(?P<environment_id>\d+)/(?P<next_page>\w+:?\w*)$', stopservice, name = 'stop'),
    url(r'^destroy/(?P<environment_id>\d+)/(?P<next_page>\w+:?\w*)$', destroyservice, name = 'destroy'),
    url(r'^refreshlogs/(?P<environment_id>\d+)$', refreshlogs, name = 'refreshlogs'),

    url(r'^configure/(?P<environment_id>\d+)$', configureservice, name = 'addproject'),  #FIXME: rename

    #FIXME: the below 2 used?
    url(r'^startproject/(?P<project_id>\d+)/(?P<next_page>\w+:?\w*)$', startprojectcontainer, name = 'startprojectcontainer'),
    url(r'^startcourse/(?P<course_id>\d+)/(?P<next_page>\w+:?\w*)$', startcoursecontainer, name = 'startcoursecontainer'),
]
