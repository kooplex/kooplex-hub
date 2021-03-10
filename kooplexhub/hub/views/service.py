import re
import logging
import requests

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
from hub.forms import table_attachments
from hub.models import Image
from hub.models import Project, UserProjectBinding
from hub.models import Service
from hub.models import Attachment, AttachmentServiceBinding
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
    pattern = request.POST.get('service', user.search.service_list)
    if pattern:
        services = Service.objects.filter(user = user, name__icontains = pattern)
    else:
        services = Service.objects.filter(user = user)
    if len(services) and pattern != user.search.service_list:
        user.search.service_list = pattern
        user.search.save()
    unbound = Service.objects.filter(user = request.user).exclude(projectservicebinding__gt = 0).exclude(reportservicebinding__gt = 0)
    if unbound:
        messages.warning(request, 'Note, your environments {} are not bound to any projects'.format(', '.join([ s.name for s in unbound ])))
    for svc in Service.objects.filter(user = request.user, state = Service.ST_NEED_RESTART):
        messages.warning(request, f'Your service {svc.name} is in inconsistent state, because {svc.restart_reasons}. Save your changes and restart them as soon as you can.')
    context_dict = {
        'next_page': 'service:list',
        'menu_container': 'active',
        'services': services,
    }
    return render(request, 'container/list.html', context = context_dict)


@login_required
def startservice(request, environment_id, next_page):
    """Starts the container."""
    user = request.user
    try:
        svc = Service.objects.get(user = user, id = environment_id)
        if svc.state == Service.ST_NOTPRESENT:
            if svc.start().wait(timeout = 10):
                messages.info(request, f'Service {svc.name} is started.')
            else:
                messages.warning(request, f'Service {svc.name} did not start within 10 seconds, reload the page later to check if it is already ready.')
        elif svc.state == Service.ST_STOPPING:
            messages.warning(request, f'Wait a second service {svc.name} is still stopping.')
        elif svc.state == Service.ST_STARTING:
            messages.warning(request, f'Wait a second service {svc.name} is starting.')
        else:
            messages.warning(request, f'Not starting service {svc.name}, which is already running.')
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
            logger.debug(f'wait_until_ready {environment.url_public}')
            environment.wait_until_ready()
            logger.debug(f'try to redirect to url {environment.url_public}')
            if environment.default_proxy.token_as_argument:
                return custom_redirect(environment.url_public, token = environment.user.profile.token)
            else:
                return custom_redirect(environment.url_public)
        else:
            messages.error(request, f'Cannot open {environment.name} of state {environment.state}')
    except Service.DoesNotExist:
        messages.error(request, 'Environment is missing')
    except requests.TooManyRedirects:
        messages.error(request, f'Cannot redirect to url {environment.url_public}')
    return redirect(next_page)


@login_required
def stopservice(request, environment_id, next_page):
    """Stops a container"""
    user = request.user
    try:
        svc = Service.objects.get(user = user, id = environment_id)
        if svc.stop().wait(timeout = 10):
            messages.info(request, f'Service {svc.name} is stopped.')
        else:
            messages.warning(request, f'Service {svc.name} did not stop within 10 seconds, reload the page later to recheck its state.')
    except Service.DoesNotExist:
        messages.error(request, 'Environment does not exist')
    except Exception as e:
        logger.error(f'Cannot stop the environment {svc} -- {e}')
        messages.error(request, f'Cannot stop environment {e}')
    return redirect(next_page)


@login_required
def restartservice(request, environment_id, next_page):
    """Restart a container"""
    user = request.user
    try:
        svc = Service.objects.get(user = user, id = environment_id)
        ev = svc.restart()
        if ev.wait(timeout = 10):
            messages.info(request, f'Service {svc.name} is restarted.')
        else:
            messages.warning(request, f'Service {svc.name} was stopped and it did not start within 10 seconds, reload the page later to recheck its state.')
    except Service.DoesNotExist:
        messages.error(request, 'Environment does not exist')
    except Exception as e:
        logger.error(f'Cannot restart the environment {svc} -- {e}')
        messages.error(request, f'Cannot restart environment: {e}')
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
    user = request.user
    logger.debug("user %s method %s" % (user, request.method))

    search = request.POST.get('button', '') == 'search'
    cancel = request.POST.get('button', '') == 'cancel'
    submit = request.POST.get('button', '') == 'apply'

    if cancel:
        return redirect('service:list')

    try:
        svc = Service.objects.get(id = environment_id, user = user)
    except Service.DoesNotExist:
        messages.error(request, 'Service environment does not exist')
        return redirect('service:list')

    if svc.state == svc.ST_STOPPING:
        messages.error(request, f'Service {svc.name} is still stopping, you cannot configure it right now.')
        return redirect('service:list')
    elif svc.state == svc.ST_STARTING:
        messages.error(request, f'Service {svc.name} is starting up, you cannot configure it right now.')
        return redirect('service:list')

    if submit:
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

        # handle attachment changes
        for id_create in request.POST.getlist('a_ids'):
            attachment = Attachment.objects.get(id = id_create)
            AttachmentServiceBinding.objects.create(service = svc, attachment = attachment)
            msg = f'associated attachment {attachment.name}'
            if not svc.mark_restart(msg):
                msgs.append(msg)
        for id_remove in set(request.POST.getlist('asb_ids_before')).difference(set(request.POST.getlist('asb_ids_after'))):
            try:
                asb = AttachmentServiceBinding.objects.get(id = id_remove, service = svc)
                msg = f'removed attachment {asb.attachment.name}'
                if not svc.mark_restart(msg):
                    msgs.append(msg)
                asb.delete()
            except AttachmentServiceBinding.DoesNotExist:
                logger.error("Is %s hacking" % user)
                oops += 1

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

        return redirect('service:list')
    else: 

        table = table_projects(svc)
        if search and request.POST.get('active_tab') == 'projects':
            pattern = request.POST.get('pattern', user.search.service_projects)
            upbs = UserProjectBinding.objects.filter(user = user, project__name__icontains = pattern)
            if len(upbs) and pattern != user.search.service_projects:
                user.search.service_projects = pattern
                user.search.save()
        elif user.search.service_projects:
            upbs = UserProjectBinding.objects.filter(user = user, project__name__icontains = user.search.service_projects)
        else:
            upbs = UserProjectBinding.objects.filter(user = user)
        table_project = table(upbs)
        RequestConfig(request).configure(table_project)

        table = table_fslibrary(svc)
        if search and request.POST.get('active_tab') == 'filesync':
            pattern = request.POST.get('pattern', user.search.service_library)
            fsls = FSLibrary.objects.filter(token__user = user, library_name__icontains = pattern).exclude(sync_folder__exact = '')
            if len(fsls) and pattern != user.search.service_library:
                user.search.service_library = pattern
                user.search.save()
        elif user.search.service_library:
            fsls = FSLibrary.objects.filter(token__user = user, library_name__icontains = user.search.service_library).exclude(sync_folder__exact = '')
        else:
            fsls = FSLibrary.objects.filter(token__user = user).exclude(sync_folder__exact = '')
        table_synclibs = table(fsls)
        RequestConfig(request).configure(table_synclibs)

        table = table_vcproject(svc)
        if search and request.POST.get('active_tab') == 'versioncontrol':
            pattern = request.POST.get('pattern', user.search.service_repository)
            vcps = VCProject.objects.filter(token__user = user, project_name__icontains = pattern).exclude(clone_folder__exact = '').exclude(clone_folder = None)
            if len(vcps) and pattern != user.search.service_repository:
                user.search.service_repository = pattern
                user.search.save()
        elif user.search.service_repository:
            vcps = VCProject.objects.filter(token__user = user, project_name__icontains = user.search.service_repository).exclude(clone_folder__exact = '').exclude(clone_folder = None)
        else:
            vcps = VCProject.objects.filter(token__user = user).exclude(clone_folder__exact = '').exclude(clone_folder = None)
        table_repos = table(vcps)
        RequestConfig(request).configure(table_repos)

        table = table_attachments(svc)
        if search and request.POST.get('active_tab') == 'attachments':
            pattern = request.POST.get('pattern', user.search.service_attachments)
            attachments = Attachment.objects.filter(name__icontains = pattern)
            if len(attachments) and pattern != user.search.service_attachments:
                user.search.service_attachments = pattern
                user.search.save()
        elif user.search.service_attachments:
            attachments = Attachment.objects.filter(name__icontains = user.search.service_attachments)
        else:
            attachments = Attachment.objects.all()
        table_attachment = table(attachments)
        RequestConfig(request).configure(table_attachment)

        context_dict = {
            'images': Image.objects.all(),
            'container': svc,
            'active': request.POST.get('active_tab', 'projects'),
            't_attachments': table_attachment,
            't_projects': table_project,
            't_synclibs': table_synclibs,
            't_repositories': table_repos,
        }
        return render(request, 'container/manage.html', context = context_dict)


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


@login_required
def layoutflip(request):
    from hub.models import Layout
    if hasattr(request.user, 'layout'):
        l = request.user.layout
        l.service_list = not l.service_list
        l.save()
    else:
        Layout.objects.create(user = request.user)
    return redirect('service:list')


@login_required
def newimage(request):
    raise NotImplementedError("TBA")


@login_required
def newattachment(request):
    try:
        assert request.user.profile.can_createattachment, f"user {request.user} is not allowed to create attachment"
        attachment = Attachment.objects.create(
            name = request.POST.get('name'),
            folder = request.POST.get('folder'),
            description = request.POST.get('description'),
            creator = request.user
            )
        logger.info(f'+ new attachment {attachment.name} by {request.user}')
        messages.info(request, f'Created attachment {attachment.name} and folder {attachment.folder}. Attach to a container to populate with data.')
    except Exception as e:
        logger.error(f'attachment not created -- {e}')
        messages.error(request, f'Attachment not created.')
    return redirect('service:list')


@login_required
def listattachment(request):
    """List attachments"""
    user = request.user
    logger.debug("user %s method %s" % (user, request.method))

    context_dict = {
        'attachments': Attachment.objects.all(),
    }
    return render(request, 'container/attachments.html', context = context_dict)


urlpatterns = [
    url(r'^new/?$', new, name = 'new'), 
    url(r'^list/?$', listservices, name = 'list'), 
    url(r'^l_search/?$', listservices, name = 'l_search'), 
    url(r'^start/(?P<environment_id>\d+)/(?P<next_page>\w+:?\w*)$', startservice, name = 'start'),
    url(r'^open/(?P<environment_id>\d+)/(?P<next_page>\w+:?\w*)$', openservice, name = 'open'),
    url(r'^stop/(?P<environment_id>\d+)/(?P<next_page>\w+:?\w*)$', stopservice, name = 'stop'),
    url(r'^restart/(?P<environment_id>\d+)/(?P<next_page>\w+:?\w*)$', restartservice, name = 'restart'),
    url(r'^destroy/(?P<environment_id>\d+)/(?P<next_page>\w+:?\w*)$', destroyservice, name = 'destroy'),
    url(r'^refreshlogs/(?P<environment_id>\d+)$', refreshlogs, name = 'refreshlogs'),
    url(r'^configure/(?P<environment_id>\d+)$', configureservice, name = 'configure'),
    url(r'^c_search/(?P<environment_id>\d+)$', configureservice, name = 'c_search'),
    url(r'^layoutflip/?$', layoutflip, name = 'layout_flip'), 
    url(r'^newimage/?$', newimage, name = 'newimage'), 
    url(r'^newattachment/?$', newattachment, name = 'newattachment'), 
    url(r'^listattachments/?$', listattachment, name = 'list_attachments'), 
]
