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
from hub.forms import table_vcproject
from hub.models import Image
from hub.models import Project, UserProjectBinding
from hub.models import Service
from hub.models import ProjectServiceBinding
from hub.models import FSLibrary, FSLibraryServiceBinding
from hub.models import VCProject, VCProjectServiceBinding

logger = logging.getLogger(__name__)

@login_required
def new(request):
    logger.debug("user %s" % request.user)
    user = request.user
    user_id = request.POST.get('user_id')
    try:
        assert user_id is not None and int(user_id) == user.id, "user id mismatch: %s tries to save %s %s" % (request.user, request.user.id, request.POST.get('user_id'))
        servicename = standardize_str(request.POST.get('name'))
        image = Image.objects.get(id = request.POST.get('image'))
        env, created = Service.objects.get_or_create(user = user, name = servicename, image = image)
        assert created, f"Service environment with name {servicename} is not unique"
        messages.info(request, f'Your new service environment {servicename} is created')
    except Exception as e:
        logger.error("New container not created -- %s" % e)
        messages.error(request, 'Error: %s' % e)
    return redirect('service:list')
        

@login_required
def listservices(request):
    """Renders the containerlist page."""
    user = request.user
    logger.debug(f'Rendering service.html {user}')
    pattern_name = request.POST.get('service', '')
    if pattern_name:
        services = Service.objects.filter(user = user, name__icontains = pattern_name)
    else:
        services = Service.objects.filter(user = user)
    unbound = Service.objects.filter(user = request.user).exclude(projectservicebinding__gt = 0)
    if unbound:
        messages.warning(request, 'Note, your environments {} are not bound to any projects'.format(', '.join([ s.name for s in unbound ])))
    for svc in Service.objects.filter(user = request.user, state = Service.ST_NEED_RESTART):
        messages.warning(request, f'Your service {svc.name} is in inconsistent state, because {svc.restart_reasons}. Save your changes and restart them as soon as you can.')
    context_dict = {
        'next_page': 'service:list',
        'menu_container': 'active',
        'services': services,
        'search_form': { 'action': "service:l_search", 'items': [ { 'name': "service", 'placeholder': "service name", 'value': pattern_name } ] },
    }
    return render(request, 'container/list.html', context = context_dict)


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
            if environment.default_proxy.token_as_argument:
                return custom_redirect(environment.url_public, token = environment.user.profile.token)
            else:
                return custom_redirect(environment.url_public)
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

        table = table_vcproject(svc)
        table_repos = table(VCProject.objects.filter(token__user = user).exclude(clone_folder__exact = ''))
        RequestConfig(request).configure(table_repos)

        context_dict = {
            'images': Image.objects.all(),
            'container': svc,
            't_projects': table_project,
            't_synclibs': table_synclibs,
            't_repositories': table_repos,
            'next_page': 'service:list',
        }
        return render(request, 'container/manage.html', context = context_dict)
    else:
        msgs = []

        # handle image change
        image_before = svc.image
        image_after = Image.objects.get(id = request.POST.get('container_image_id'))
        if image_before != image_after:
            svc.image = image_after
            svc.save()
            msg = f'image changed from {image_before} to {image_after}'
            if not svc.mark_restart(msg):
                msgs.append(msg)

        # handle project binding changes
        project_ids_before = set(request.POST.getlist('project_ids_before'))
        project_ids_after = set(request.POST.getlist('project_ids_after'))
        oops = 0
        for project_id in project_ids_after.difference(project_ids_before):
            try:
                project = Project.get_userproject(project_id = project_id, user = user)
                ProjectServiceBinding.objects.create(service = svc, project = project)
                msg = f'project {project.name} added'
                if not svc.mark_restart(msg):
                    msgs.append(msg)
                logger.debug('added project %s to container %s' % (project, svc))
            except Exception as e:
                logger.error('not authorized to add project_id %s to container %s -- %s' % (project_id, svc, e))
                oops += 1
        for project_id in project_ids_before.difference(project_ids_after):
            try:
                project = Project.get_userproject(project_id = project_id, user = user)
                ProjectServiceBinding.objects.get(service = svc, project = project).delete()
                msg = f'project {project.name} removed'
                if not svc.mark_restart(msg):
                    msgs.append(msg)
                logger.debug('removed project %s from container %s' % (project, svc))
            except Exception as e:
                logger.error('not authorized to remove project_id %s from container %s -- %s' % (project_id, svc, e))
                oops += 1

        # handle synchron caches
        for id_create in request.POST.getlist('fsl_ids'):
            fsl = FSLibrary.objects.get(id = id_create)
            if fsl.token.user != user:
                logger.error("Unauthorized request fsl: %s, user: %s" % (fsl, user))
                oops += 1
                continue
            FSLibraryServiceBinding.objects.create(service = svc, fslibrary = fsl)
            msg = f'synchron library {fsl.library_name} attached'
            if not svc.mark_restart(msg):
                msgs.append(msg)
        for id_remove in set(request.POST.getlist('fslpb_ids_before')).difference(set(request.POST.getlist('fslpb_ids_after'))):
            try:
                fslsb = FSLibraryServiceBinding.objects.get(id = id_remove, service = svc)
                if fslsb.fslibrary.token.user != user:
                    logger.error("Unauthorized request fsl: %s, user: %s" % (fslsb.fslibrary, user))
                    oops += 1
                    continue
                msg = f'synchron library {fslsb.fslibrary.library_name} removed'
                if not svc.mark_restart(msg):
                    msgs.append(msg)
                fslsb.delete()
            except FSLibraryServiceBinding.DoesNotExist:
                logger.error("Is %s hacking" % user)
                oops += 1

        # handle repository caches
        for id_create in request.POST.getlist('vcp_ids'):
            vcp = VCProject.objects.get(id = id_create)
            if vcp.token.user != user:
                logger.error("Unauthorized request vcp: %s, user: %s" % (vcp, user))
                oops += 1
                continue
            VCProjectServiceBinding.objects.create(service = svc, vcproject = vcp)
            msg = f'version control project {vcp.project_name} attached'
            if not svc.mark_restart(msg):
                msgs.append(msg)
        for id_remove in set(request.POST.getlist('vcpsb_ids_before')).difference(set(request.POST.getlist('vcpsb_ids_after'))):
            try:
                vcpsb = VCProjectServiceBinding.objects.get(id = id_remove, service = svc)
                if vcpsb.vcproject.token.user != user:
                    logger.error("Unauthorized request vcp: %s, user: %s" % (vcpsb.vcproject, user))
                    oops += 1
                    continue
                msg = f'version control project {vcpsb.vcproject.project_name} removed'
                if not svc.mark_restart(msg):
                    msgs.append(msg)
                vcpsb.delete()
            except VCProjectServiceBinding.DoesNotExist:
                logger.error("Is %s hacking" % user)
                oops += 1

        if svc.restart_reasons:
            messages.warning(request, f'Configuration of {svc.name} is done, but needs a restart because {svc.restart_reasons}.')
        if msgs:
            messages.info(request, 'Configuration of {} is done. Summary: {}.'.format(svc.name, ', '.join(msgs)))
        if oops:
            messages.warning(request, 'Some problems (%d) occured during handling yout request.' % (oops))

        return redirect(next_page)


@login_required
def refreshlogs(request, environment_id):
    user = request.user
    try:
        svc = Service.objects.get(user = user, id = environment_id)
        svc.check_state()
    except Service.DoesNotExist:
        messages.error(request, 'Environment does not exist')
    except Exception as e:
        logger.error(f'Cannot refresh service environment information {svc} -- {e}')
        messages.error(request, f'Cannot refresh service environment information {svc}')
    return redirect('service:list')

urlpatterns = [
    url(r'^new/?$', new, name = 'new'), 
    url(r'^list/?$', listservices, name = 'list'), 
    url(r'^l_search/?$', listservices, name = 'l_search'), 
    url(r'^start/(?P<environment_id>\d+)/(?P<next_page>\w+:?\w*)$', startservice, name = 'start'),
    url(r'^open/(?P<environment_id>\d+)/(?P<next_page>\w+:?\w*)$', openservice, name = 'open'),
    url(r'^stop/(?P<environment_id>\d+)/(?P<next_page>\w+:?\w*)$', stopservice, name = 'stop'),
    url(r'^destroy/(?P<environment_id>\d+)/(?P<next_page>\w+:?\w*)$', destroyservice, name = 'destroy'),
    url(r'^refreshlogs/(?P<environment_id>\d+)$', refreshlogs, name = 'refreshlogs'),
    url(r'^configure/(?P<environment_id>\d+)$', configureservice, name = 'configure'),
]
