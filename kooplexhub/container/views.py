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


@login_required
def destroy(request, pk):
    """Deletes a container instance"""
    user = request.user
    container = Container.objects.filter(id = pk, user = user).first()
    if container:
        logger.debug(f'deleting {container}')
        container.stop()
        container.delete()
        messages.info(request, f'Your environment {container.name} is deleted.')
    return redirect('container:list')


class ContainerListView(LoginRequiredMixin, generic.ListView):
    template_name = 'container_list.html'
    context_object_name = 'containers'
    model = Container

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['menu_container'] = True
        context['wss_container_fetchlog'] = KOOPLEX.get('hub', {}).get('wss_container_fetchlog', 'wss://localhost/hub/ws/container/fetchlog/{userid}/').format(userid = self.request.user.id)
        context['wss_container_config'] = KOOPLEX.get('hub', {}).get('wss_container_config', 'wss://localhost/hub/ws/container/config/{userid}/').format(userid = self.request.user.id)
        context['wss_container_control'] = KOOPLEX.get('hub', {}).get('wss_container_control', 'wss://localhost/hub/ws/container/control/{userid}/').format(userid = self.request.user.id)
        context['wss_monitor_node'] = KOOPLEX.get('hub', {}).get('wss_monitor_node', 'wss://localhost/hub/ws/monitor/node/{userid}/').format(userid = self.request.user.id)
        context['t_project'] = TableProject(self.request.user)
        context['t_course'] = TableCourse(self.request.user)
        context['t_volume'] = TableVolume(self.request.user)
        context['resource_form']=FormContainer(initial={'user': self.request.user})
        context['images'] = Image.objects.filter(imagetype = Image.TP_PROJECT, present = True)
        context['empty_container'] = Container()
        context['search_placeholder'] = 'Search container...'
        context['search_what'] = 'container'
        return context

    def get_queryset(self):
        user = self.request.user
        containers = Container.objects.filter(user = user).order_by('name')
        return containers



@login_required
def open(request, pk):
    """Opens a container"""
    user = request.user
    try:
        container = Container.objects.get(id = pk, user = user)
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

