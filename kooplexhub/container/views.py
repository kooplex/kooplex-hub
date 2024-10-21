import logging
import json
import requests
import re

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import redirect
from django.utils.html import format_html
from django.views import generic
from django.urls import reverse
from django.contrib.auth.mixins import LoginRequiredMixin

from .forms import FormContainer
from .forms import TableProject, TableCourse, TableVolume,                        TableContainerProject, TableContainerCourse, TableContainerVolume
from .models import Image, Container
from project.models import Project, UserProjectBinding, ProjectContainerBinding
from education.models import Course, UserCourseBinding, CourseContainerBinding
from volume.models import Volume, VolumeContainerBinding

from kooplexhub.lib import custom_redirect

from kooplexhub import settings
from .lib import Cluster

KOOPLEX = settings.KOOPLEX

logger = logging.getLogger(__name__)


class ContainerView(LoginRequiredMixin, generic.FormView):
    model = Container
    template_name = 'container.html'
    form_class = FormContainer
    success_url = '/hub/container_environment/list/' #FIXME: django.urls.reverse or shortcuts.reverse does not work reverse('project:list')

    def get_initial(self):
        initial = super().get_initial()
        user = self.request.user
        initial['user'] = user
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        container_id = self.kwargs.get('pk')
        context['menu_container'] = True
        context['submenu'] = 'configure' if container_id else 'new' 
        context['active'] = self.request.COOKIES.get('configure_env_tab', 'meta') if container_id else 'meta'
        context['url_post'] = reverse('container:configure', args = (container_id, )) if container_id else reverse('container:new')
        context['url_list'] = reverse('container:list')
        context['wss_container'] = KOOPLEX.get('hub', {}).get('wss_container', 'wss://localhost/hub/ws/container_environment/{userid}/').format(userid = self.request.user.id)
        context['wss_monitor'] = KOOPLEX.get('hub', {}).get('wss_monitor', 'wss://localhost/hub/ws/node_monitor/')
        context['container_id'] = container_id
        context['containers'] = Container.objects.filter(user = self.request.user).order_by('name')
        context['partial'] = 'container_partial_list.html'
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        api = Cluster()
        api.query_nodes_status()
        kwargs['nodes'] = list(api.node_df['node'].values)
        return kwargs

    def form_valid(self, form):
        logger.info(form.cleaned_data)
        user = self.request.user
        container_config = form.cleaned_data.pop('container_config')
        assert user.id == container_config['user_id']
        container_id = container_config['container_id']
        #FIXME:
        if container_id == 'None':
            container_id = None
        ##
        msgs = []
        if container_id:
            container = Container.objects.get(id = container_id)
            att_r = []
            for att in [ 'image', 'idletime', 'cpurequest', 'gpurequest', 'memoryrequest' ]:
                if getattr(container, att) != form.cleaned_data[att]:
                    att_r.append(att)
            if att_r:
                msgs.append("Attribute(s) changed: {}".format(', '.join(att_r)))
                container.mark_restart(msgs[-1])
        else:
            container = Container.objects.create(**form.cleaned_data)
            msgs.append(f'Container {container} created.')
        # handle projects
        project_add = []
        for project in container_config['bind_projects']:
            _, created = ProjectContainerBinding.objects.get_or_create(project = project, container = container)
            if created:
                project_add.append(str(project))
        if project_add:
            msgs.append('Project(s) associated with container: {}.'.format(', '.join(project_add)))
            container.mark_restart(msgs[-1])
        remove = ProjectContainerBinding.objects.filter(container = container).exclude(project__in = container_config['bind_projects'])
        remove.delete()
        if remove:
            msgs.append('Project(s) disconnected from container: {}.'.format(', '.join([ str(b.project) for b in remove ])))
            container.mark_restart(msgs[-1])
        # handle courses
        course_add = []
        for course in container_config['bind_courses']:
            _, created = CourseContainerBinding.objects.get_or_create(course = course, container = container)
            if created:
                course_add.append(str(course))
        if course_add:
            msgs.append('Course(s) associated with container: {}.'.format(', '.join(course_add)))
            container.mark_restart(msgs[-1])
        remove = CourseContainerBinding.objects.filter(container = container).exclude(course__in = container_config['bind_courses'])
        remove.delete()
        if remove:
            msgs.append('Course(s) disconnected from container: {}.'.format(', '.join([ str(b.course) for b in remove ])))
            container.mark_restart(msgs[-1])
        # handle volumes
        volume_add = []
        for volume in container_config['bind_volumes']:
            _, created = VolumeContainerBinding.objects.get_or_create(volume = volume, container = container)
            if created:
                volume_add.append(str(volume))
        if volume_add:
            msgs.append('Volume(s)/attachment(s) associated with container: {}.'.format(', '.join(volume_add)))
            container.mark_restart(msgs[-1])
        remove = VolumeContainerBinding.objects.filter(container = container).exclude(volume__in = container_config['bind_volumes'])
        remove.delete()
        if remove:
            msgs.append('Volume(s)/attachment(s) disconnected from container: {}.'.format(', '.join([ str(b.volume) for b in remove ])))
            container.mark_restart(msgs[-1])
        if msgs:
            messages.info(self.request, ' '.join(msgs))
        return super().form_valid(form)


class NewContainerView(ContainerView, generic.FormView):
    pass


class ConfigureContainerView(ContainerView, generic.edit.UpdateView):
    pass


@login_required
def destroy(request, container_id):
    """Deletes a container instance"""
    user = request.user
    try:
        container = Container.objects.get(id = container_id, user = user)
        container.stop()
        container.delete()
        messages.info(request, f'Your environment {container.name} is deleted.')
    except Container.DoesNotExist:
        messages.error(request, 'Container environment does not exist')
    return redirect('container:list')


class ContainerListView(LoginRequiredMixin, generic.ListView):
    template_name = 'container_list.html'
    context_object_name = 'containers'
    model = Container

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        container_id = self.request.COOKIES.get('search_container_id', None)
        if container_id:
            c = Container.objects.get(id = container_id)
            context["search_container"] = c.search
        l = reverse('container:new')
        context['menu_container'] = True
        context['submenu'] = 'list'
        context['partial'] = 'container_partial_list.html'
        context['wss_container_fetchlog'] = KOOPLEX.get('hub', {}).get('wss_container_fetchlog', 'wss://localhost/hub/ws/container/fetchlog/{userid}/').format(userid = self.request.user.id)
        context['wss_container_config'] = KOOPLEX.get('hub', {}).get('wss_container_config', 'wss://localhost/hub/ws/container/config/{userid}/').format(userid = self.request.user.id)
        context['wss_container_control'] = KOOPLEX.get('hub', {}).get('wss_container_control', 'wss://localhost/hub/ws/container/control/{userid}/').format(userid = self.request.user.id)
        context['wss_monitor_node'] = KOOPLEX.get('hub', {}).get('wss_monitor_node', 'wss://localhost/hub/ws/monitor/node/{userid}/').format(userid = self.request.user.id)
        context['t_project'] = TableProject(self.request.user)
        context['t_course'] = TableCourse(self.request.user)
        context['t_volume'] = TableVolume(self.request.user)
        context['url_list'] = reverse('container:list')
        context['resource_form']=FormContainer(initial={'user': self.request.user})
        context['images'] = Image.objects.filter(imagetype = Image.TP_PROJECT, present = True)
        return context

    def get_queryset(self):
        user = self.request.user
        containers = Container.objects.filter(user = user).order_by('name')
        return containers

#DEPRECATED   class ReportContainerListView(LoginRequiredMixin, generic.ListView):
#DEPRECATED       template_name = 'container_list.html'
#DEPRECATED       context_object_name = 'containers'
#DEPRECATED       model = Container
#DEPRECATED   
#DEPRECATED       def get_context_data(self, **kwargs):
#DEPRECATED           l = reverse('report:new')
#DEPRECATED           context = super().get_context_data(**kwargs)
#DEPRECATED           context['menu_container'] = True
#DEPRECATED           context['submenu'] = 'reportclist'
#DEPRECATED           context['partial'] = 'container_partial_list_report.html'
#DEPRECATED           context['empty'] = format_html(f"""You need to <a href="{l}"><i class="bi bi-projector"></i><span>&nbsp;create</span></a> a container backed report to see here anything useful.""")
#DEPRECATED           return context
#DEPRECATED   
#DEPRECATED       def get_queryset(self):
#DEPRECATED           user = self.request.user
#DEPRECATED           containers = Container.objects.filter(user = user, image__imagetype = Image.TP_REPORT).order_by('name')
#DEPRECATED           return containers


@login_required
def open(request, container_id):
    """Opens a container"""
    user = request.user
    try:
        container = Container.objects.get(id = container_id, user = user)
        if container.state in [ Container.ST_RUNNING, Container.ST_NEED_RESTART ]:
            logger.debug(f'wait_until_ready {container.url_notebook}')
            container.wait_until_ready()
            logger.debug(f'try to redirect to url {container.url_notebook}')
            if container.default_proxy.token_as_argument:
                return custom_redirect(container.url_notebook, token = container.user.profile.token)
            else:
                return custom_redirect(container.url_notebook)
        else:
            messages.error(request, f'Cannot open {container.name} of state {container.state}')
    except Container.DoesNotExist:
        messages.error(request, 'Environment is missing')
    except requests.TooManyRedirects:
        messages.error(request, f'Cannot redirect to url {container.url_notebook}')
    except Exception as e:
        logger.error(f'cannot redirect to url {container.url_notebook} -- {e}')
        messages.error(request, f'Cannot redirect to url {container.url_notebook}')
    return redirect('container:list')

#@login_required
#def report_open(request, container_id):
#    """Opens the report_url for a container"""
#    user = request.user
#    try:
#        container = Container.objects.get(id = container_id, user = user)
#        if container.state in [ Container.ST_RUNNING, Container.ST_NEED_RESTART ]:
#            logger.debug(f'wait_until_ready {container.url_notebook}')
#            container.wait_until_ready()
#            logger.debug(f'try to redirect to url {container.url_notebook}')
#            if container.default_proxy.token_as_argument:
#                return custom_redirect(container.url_notebook, token = container.user.profile.token)
#            else:
#                return custom_redirect(container.url_notebook)
#        else:
#            messages.error(request, f'Cannot open {container.name} of state {container.state}')
#    except Container.DoesNotExist:
#        messages.error(request, 'Environment is missing')
#    except requests.TooManyRedirects:
#        messages.error(request, f'Cannot redirect to url {container.url_notebook}')
#    except Exception as e:
#        logger.error(f'cannot redirect to url {container.url_notebook} -- {e}')
#        messages.error(request, f'Cannot redirect to url {container.url_notebook}')
#    return redirect('container:list')
