import logging
import json
import requests

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import redirect
from django.views import generic
from django.contrib.auth.mixins import LoginRequiredMixin

from django_tables2 import RequestConfig

from .forms import FormContainer, FormAttachment
from .forms import TableContainerProject, TableContainerCourse, TableContainerAttachment
from .models import Image, Container, Attachment, AttachmentContainerBinding
from project.models import Project, UserProjectBinding, ProjectContainerBinding
from education.models import Course, UserCourseBinding, CourseContainerBinding

from kooplexhub.lib import custom_redirect

from kooplexhub import settings

logger = logging.getLogger(__name__)

@login_required
def new(request):
    logger.debug("user %s" % request.user)
    user = request.user
    user_id = request.POST.get('user_id')
    try:
        assert user_id is not None and int(user_id) == user.id, "user id mismatch: %s tries to save %s %s" % (request.user, request.user.id, request.POST.get('user_id'))
        form = FormContainer(request.POST)
        if form.is_valid():
            logger.info(form.cleaned_data)
            env, created = Container.objects.get_or_create(
                    user = user, 
                    name = form.cleaned_data['name'], 
                    friendly_name = form.cleaned_data['friendly_name'], 
                    image = form.cleaned_data['image']
            )
            assert created, f"Service environment with name {form.cleaned_data['name']} is not unique"
            messages.info(request, f'Your new service environment {form.cleaned_data["friendly_name"]} is created')
        else:
            messages.error(request, form.errors)
    except Exception as e:
        logger.error("New container not created -- %s" % e)
        messages.error(request, 'Error: %s' % e)
    return redirect('container:list')


@login_required
def destroy(request, container_id, next_page):
    """Deletes a container instance"""
    user = request.user
    try:
        container = Container.objects.get(id = container_id, user = user)
        container.stop()
        container.delete()
    except Container.DoesNotExist:
        messages.error(request, 'Container environment does not exist')
    return redirect(next_page)


@login_required
def layout_flip(request):
    profile = request.user.profile
    profile.layout_container_list ^= True
    profile.save()
    return redirect('container:list')


class ContainerListView(LoginRequiredMixin, generic.ListView):
    template_name = 'container_list.html'
    context_object_name = 'containers'
    model = Container

    def get_queryset(self):
        user = self.request.user
        profile = user.profile
        pattern = self.request.GET.get('container', profile.search_container_list)
        if pattern:
            containers = Container.objects.filter(user = user, name__icontains = pattern).order_by('name')
        else:
            containers = Container.objects.filter(user = user).order_by('name')
        if len(containers) and pattern != profile.search_container_list:
            profile.search_container_list = pattern
            profile.save()
        return containers


class AttachmentListView(LoginRequiredMixin, generic.ListView):
    template_name = 'attachment_list.html'
    context_object_name = 'attachments'
    model = Attachment

    def get_queryset(self):
        user = self.request.user
        profile = user.profile
        pattern = self.request.GET.get('attachment', profile.search_attachment_list)
        if pattern:
            attachments = Attachment.objects.filter(name__icontains = pattern).order_by('name')
        else:
            attachments = Attachment.objects.all().order_by('name')
        if len(attachments) and pattern != profile.search_attachment_list:
            profile.search_attachment_list = pattern
            profile.save()
        return attachments


@login_required
def new_attachment(request):
    logger.debug("user %s" % request.user)
    user = request.user
    user_id = request.POST.get('user_id')
    try:
        assert user_id is not None and int(user_id) == user.id, "user id mismatch: %s tries to save %s %s" % (request.user, request.user.id, request.POST.get('user_id'))
        form = FormAttachment(request.POST)
        if form.is_valid():
            logger.info(form.cleaned_data)
            attachment, created = Attachment.objects.get_or_create(creator_id = user_id, name = form.cleaned_data['name'], folder = form.cleaned_data['folder'], description = form.cleaned_data['description'])
            assert created, f"Attachment with name {form.cleaned_data['name']} is not unique"
            messages.info(request, f'New attachment {form.cleaned_data["name"]} is created')
        else:
            messages.error(request, form.errors)
    except Exception as e:
        logger.error("Attachment not created -- %s" % e)
        messages.error(request, 'Error: %s' % e)
    return redirect('container:list_attachments')


@login_required
def configure(request, container_id):
    """Manage your projects"""
    user = request.user
    profile = user.profile
    logger.debug("user %s method %s" % (user, request.method))

    if request.POST.get('button', '') == 'cancel':
        return redirect('container:list')
    try:
        svc = Container.objects.get(id = container_id, user = user)
        svc.collapsed = False
        svc.save()
    except Container.DoesNotExist:
        messages.error(request, 'Service environment does not exist')
        return redirect('container:list')

    if svc.state == svc.ST_STOPPING:
        messages.error(request, f'Service {svc.name} is still stopping, you cannot configure it right now.')
        return redirect('container:list')
    elif svc.state == svc.ST_STARTING:
        messages.error(request, f'Service {svc.name} is starting up, you cannot configure it right now.')
        return redirect('container:list')

    oops = 0
    if request.POST.get('button', '') == 'apply':
        msgs = []

        # handle name change
        friendly_name_before = svc.friendly_name
        friendly_name_after = request.POST.get('friendly_name')
        if friendly_name_before != friendly_name_after:
            svc.friendly_name = friendly_name_after
            svc.save()

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
            AttachmentContainerBinding.objects.create(container = svc, attachment = attachment)
            msg = f'associated attachment {attachment.name}'
            if not svc.mark_restart(msg):
                msgs.append(msg)
        for id_remove in set(request.POST.getlist('asb_ids_before')).difference(set(request.POST.getlist('asb_ids_after'))):
            try:
                asb = AttachmentContainerBinding.objects.get(id = id_remove, container = svc)
                msg = f'removed attachment {asb.attachment.name}'
                if not svc.mark_restart(msg):
                    msgs.append(msg)
                asb.delete()
            except AttachmentContainerBinding.DoesNotExist:
                logger.error("Is %s hacking" % user)
                oops += 1

        # handle project binding changes
        if 'project' in settings.INSTALLED_APPS:
            project_ids_before = set(request.POST.getlist('project_ids_before'))
            project_ids_after = set(request.POST.getlist('project_ids_after'))
            for project_id in project_ids_after.difference(project_ids_before):
                try:
                    project = Project.get_userproject(project_id = project_id, user = user)
                    ProjectContainerBinding.objects.create(container = svc, project = project)
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
                    ProjectContainerBinding.objects.get(container = svc, project = project).delete()
                    msg = f'project {project.name} removed'
                    if not svc.mark_restart(msg):
                        msgs.append(msg)
                    logger.debug('removed project %s from container %s' % (project, svc))
                except Exception as e:
                    logger.error('not authorized to remove project_id %s from container %s -- %s' % (project_id, svc, e))
                    oops += 1

        # handle course binding changes
        if 'education' in settings.INSTALLED_APPS:
            course_ids_before = set(request.POST.getlist('course_ids_before'))
            course_ids_after = set(request.POST.getlist('course_ids_after'))
            for course_id in course_ids_after.difference(course_ids_before):
                try:
                    course = Course.get_usercourse(course_id = course_id, user = user)
                    CourseContainerBinding.objects.create(container = svc, course = course)
                    msg = f'course {course.name} added'
                    if not svc.mark_restart(msg):
                        msgs.append(msg)
                    logger.debug('added course %s to container %s' % (course, svc))
                except Exception as e:
                    logger.error('not authorized to add course_id %s to container %s -- %s' % (course_id, svc, e))
                    oops += 1
            for course_id in course_ids_before.difference(course_ids_after):
                try:
                    course = Course.get_usercourse(course_id = course_id, user = user)
                    CourseContainerBinding.objects.get(container = svc, course = course).delete()
                    msg = f'course {course.name} removed'
                    if not svc.mark_restart(msg):
                        msgs.append(msg)
                    logger.debug('removed course %s from container %s' % (course, svc))
                except Exception as e:
                    logger.error('not authorized to remove course_id %s from container %s -- %s' % (course_id, svc, e))
                    oops += 1

        if 'plugin' in settings.INSTALLED_APPS:
            # handle synchron caches
            for id_create in request.POST.getlist('fsl_ids'):
                fsl = FSLibrary.objects.get(id = id_create)
                if fsl.token.user != user:
                    logger.error("Unauthorized request fsl: %s, user: %s" % (fsl, user))
                    oops += 1
                    continue
                FSLibraryServiceBinding.objects.create(container = svc, fslibrary = fsl)
                msg = f'synchron library {fsl.library_name} attached'
                if not svc.mark_restart(msg):
                    msgs.append(msg)
            for id_remove in set(request.POST.getlist('fslpb_ids_before')).difference(set(request.POST.getlist('fslpb_ids_after'))):
                try:
                    fslsb = FSLibraryServiceBinding.objects.get(id = id_remove, container = svc)
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
                VCProjectContainerBinding.objects.create(container = svc, vcproject = vcp)
                msg = f'version control project {vcp.project_name} attached'
                if not svc.mark_restart(msg):
                    msgs.append(msg)
            for id_remove in set(request.POST.getlist('vcpsb_ids_before')).difference(set(request.POST.getlist('vcpsb_ids_after'))):
                try:
                    vcpsb = VCProjectContainerBinding.objects.get(id = id_remove, container = svc)
                    if vcpsb.vcproject.token.user != user:
                        logger.error("Unauthorized request vcp: %s, user: %s" % (vcpsb.vcproject, user))
                        oops += 1
                        continue
                    msg = f'version control project {vcpsb.vcproject.project_name} removed'
                    if not svc.mark_restart(msg):
                        msgs.append(msg)
                    vcpsb.delete()
                except VCProjectContainerBinding.DoesNotExist:
                    logger.error("Is %s hacking" % user)
                    oops += 1

        if svc.restart_reasons:
            messages.warning(request, f'Configuration of {svc.name} is done, but needs a restart because {svc.restart_reasons}.')
        if msgs:
            messages.info(request, 'Configuration of {} is done. Summary: {}.'.format(svc.name, ', '.join(msgs)))
        if oops:
            messages.warning(request, 'Some problems (%d) occured during handling yout request.' % (oops))

        return redirect('container:list')
    else:
        active_tab = request.GET.get('active_tab', 'projects')

        pattern = request.GET.get('pattern', profile.search_container_projects) if active_tab == 'projects' else profile.search_container_projects
        if pattern:
            upbs = UserProjectBinding.objects.filter(user = user, project__name__icontains = pattern)
        else:
            upbs = UserProjectBinding.objects.filter(user = user)
        if len(upbs) and pattern != profile.search_container_projects:
            profile.search_container_projects = pattern
            profile.save()
        table_project = TableContainerProject(svc, upbs)
        RequestConfig(request).configure(table_project)

        #pattern = request.GET.get('pattern', profile.search_container_courses) if active_tab == 'courses' else profile.search_container_courses
        #if pattern:
        #    ucbs = UserCourseBinding.objects.filter(user = user, course__name__icontains = pattern)
        #else:
        #    ucbs = UserCourseBinding.objects.filter(user = user)
        ucbs = UserCourseBinding.objects.filter(user = user)
        #if len(ucbs) and pattern != profile.search_container_courses:
        #    profile.search_container_projects = pattern
        #    profile.save()
        table_course = TableContainerCourse(svc, ucbs)
        #RequestConfig(request).configure(table_course)

        pattern = request.GET.get('pattern', profile.search_container_attachments) if active_tab == 'attachments' else profile.search_container_attachments
        if pattern:
            attachments = Attachment.objects.filter(name__icontains = pattern)
        else:
            attachments = Attachment.objects.all()
        if len(attachments) and pattern != profile.search_container_attachments:
            profile.search_container_attachments = pattern
            profile.save()
        table_attachment = TableContainerAttachment(svc, attachments)
        RequestConfig(request).configure(table_attachment)

        context_dict = {
            'images': Image.objects.filter(present = True, imagetype = Image.TP_PROJECT),
            'container': svc,
            'active': active_tab,
            't_attachments': table_attachment,
            't_projects': table_project,
            't_courses': table_course,
        }

        if 'plugin' is settings.INSTALLED_APPS:
            pass
#FIXME:        table = table_fslibrary(svc)
#FIXME:        if search and request.POST.get('active_tab') == 'filesync':
#FIXME:            pattern = request.POST.get('pattern', user.search.service_library)
#FIXME:            fsls = FSLibrary.objects.filter(token__user = user, library_name__icontains = pattern).exclude(sync_folder__exact = '')
#FIXME:            if len(fsls) and pattern != user.search.service_library:
#FIXME:                user.search.service_library = pattern
#FIXME:                user.search.save()
#FIXME:        elif user.search.service_library:
#FIXME:            fsls = FSLibrary.objects.filter(token__user = user, library_name__icontains = user.search.service_library).exclude(sync_folder__exact = '')
#FIXME:        else:
#FIXME:            fsls = FSLibrary.objects.filter(token__user = user).exclude(sync_folder__exact = '')
#FIXME:        table_synclibs = table(fsls)
#FIXME:        RequestConfig(request).configure(table_synclibs)
#FIXME:
#FIXME:        table = table_vcproject(svc)
#FIXME:        if search and request.POST.get('active_tab') == 'versioncontrol':
#FIXME:            pattern = request.POST.get('pattern', user.search.service_repository)
#FIXME:            vcps = VCProject.objects.filter(token__user = user, project_name__icontains = pattern).exclude(clone_folder__exact = '').exclude(clone_folder = None)
#FIXME:            if len(vcps) and pattern != user.search.service_repository:
#FIXME:                user.search.service_repository = pattern
#FIXME:                user.search.save()
#FIXME:        elif user.search.service_repository:
#FIXME:            vcps = VCProject.objects.filter(token__user = user, project_name__icontains = user.search.service_repository).exclude(clone_folder__exact = '').exclude(clone_folder = None)
#FIXME:        else:
#FIXME:            vcps = VCProject.objects.filter(token__user = user).exclude(clone_folder__exact = '').exclude(clone_folder = None)
#FIXME:        table_repos = table(vcps)
#FIXME:        RequestConfig(request).configure(table_repos)
#FIXME:
                #FIXME context_dict.update({
                #FIXME:            't_synclibs': table_synclibs,
                #FIXME:            't_repositories': table_repos, })
 

        return render(request, 'container_configure.html', context = context_dict)


@login_required
def start(request, container_id, next_page):
    """Starts the container."""
    user = request.user

    try:
        svc = Container.objects.get(user = user, id = container_id)
        if svc.state == Container.ST_NOTPRESENT:
            if svc.start().wait(timeout = 10):
                messages.info(request, f'Service {svc.name} is started.')
            else:
                messages.warning(request, f'Service {svc.name} did not start within 10 seconds, reload the page later to check if it is already ready.')
        elif svc.state == Container.ST_STOPPING:
            messages.warning(request, f'Wait a second service {svc.name} is still stopping.')
        elif svc.state == Container.ST_STARTING:
            messages.warning(request, f'Wait a second service {svc.name} is starting.')
        else:
            messages.warning(request, f'Not starting service {svc.name}, which is already running.')
    except Container.DoesNotExist:
        messages.error(request, 'Service environment does not exist')
    except Exception as e:
        logger.error(f'Cannot start the environment {svc} -- {e}')
        messages.error(request, f'Cannot start service environment {e}')
    return redirect(next_page)


def _get_cookie(request):
    try:
        cv = request.COOKIES.get('show_container', '[]')
        return set( json.loads( cv.replace('%5B', '[').replace('%2C', ',').replace('%5D', ']') ) )
    except Exception:
        logger.error('stupid cookie value: {cv}')
        return set()


@login_required
def refresh(request, container_id):
    user = request.user

    try:
        svc = Container.objects.get(user = user, id = container_id)
        svc.check_state()
    except Container.DoesNotExist:
        messages.error(request, 'Environment does not exist')
    except Exception as e:
        logger.error(f'Cannot refresh service environment information {svc} -- {e}')
        messages.error(request, f'Cannot refresh service environment information {svc}')
    redirection = redirect('container:list')
    shown = _get_cookie(request)
    shown.add( svc.id )
    redirection.set_cookie('show_container', json.dumps( list(shown) ))
    return redirection


@login_required
def stop(request, container_id, next_page):
    """Stops a container"""
    user = request.user
    try:
        svc = Container.objects.get(user = user, id = container_id)
        if svc.stop().wait(timeout = 10):
            messages.info(request, f'Service {svc.name} is stopped.')
        else:
            messages.warning(request, f'Service {svc.name} did not stop within 10 seconds, reload the page later to recheck its state.')
    except Container.DoesNotExist:
        messages.error(request, 'Environment does not exist')
    except Exception as e:
        logger.error(f'Cannot stop the environment {svc} -- {e}')
        messages.error(request, f'Cannot stop environment {e}')
    redirection = redirect(next_page)
    shown = _get_cookie(request)
    if svc.id in shown:
        shown.remove( svc.id )
    redirection.set_cookie('show_container', json.dumps( list(shown) ))
    return redirection


@login_required
def restart(request, container_id, next_page):
    """Restart a container"""
    user = request.user
    try:
        svc = Container.objects.get(user = user, id = container_id)
        ev = svc.restart()
        if ev.wait(timeout = 10):
            messages.info(request, f'Service {svc.name} is restarted.')
        else:
            messages.warning(request, f'Service {svc.name} was stopped and it did not start within 10 seconds, reload the page later to recheck its state.')
    except Container.DoesNotExist:
        messages.error(request, 'Environment does not exist')
    except Exception as e:
        logger.error(f'Cannot restart the environment {svc} -- {e}')
        messages.error(request, f'Cannot restart environment: {e}')
    return redirect(next_page)


@login_required
def open(request, container_id, next_page, shown = "[]"):
    """Opens a container"""
    user = request.user
    #if shown != "[]":
    #    raise Exception(shown)
    
    try:
        container = Container.objects.get(id = container_id, user = user)
        if container.state in [ Container.ST_RUNNING, Container.ST_NEED_RESTART ]:
            logger.debug(f'wait_until_ready {container.url_public}')
            container.wait_until_ready()
            logger.debug(f'try to redirect to url {container.url_public}')
            if container.default_proxy.token_as_argument:
                return custom_redirect(container.url_public, token = container.user.profile.token)
            else:
                return custom_redirect(container.url_public)
        else:
            messages.error(request, f'Cannot open {container.name} of state {container.state}')
    except Container.DoesNotExist:
        messages.error(request, 'Environment is missing')
    except requests.TooManyRedirects:
        messages.error(request, f'Cannot redirect to url {container.url_public}')
    except Exception as e:
        logger.error(f'cannot redirect to url {container.url_public} -- {e}')
        messages.error(request, f'Cannot redirect to url {container.url_public}')
    return redirect(next_page)

