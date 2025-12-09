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
from project.tables import TableProject
from education.tables import TableCourse
from volume.tables import TableVolume
from .models import Image, Container


from .lib import Cluster

from .conf import CONTAINER_SETTINGS

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
    template_name = 'container/list.html'
    context_object_name = 'containers'
    model = Container

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['menu_container'] = True
        context['wss_container_fetchlog'] = CONTAINER_SETTINGS['wss']['fetchlog'].format(user = self.request.user)
        context['wss_container_config'] = CONTAINER_SETTINGS['wss']['config'].format(user = self.request.user)
        context['wss_container_control'] = CONTAINER_SETTINGS['wss']['control'].format(user = self.request.user)
        context['wss_monitor_node'] = CONTAINER_SETTINGS['wss']['monitor_node'].format(user = self.request.user)
        context['t_project'] = TableProject.from_user(self.request.user)
        context['t_course'] = TableCourse.from_user(self.request.user)
        context['t_volume'] = TableVolume.for_user(self.request.user)
        context['resource_form']=FormContainer(initial={'user': self.request.user})
        context['images'] = Image.objects.filter(imagetype = Image.ImageType.PROJECT, present = True)
        return context

    def get_queryset(self):
        user = self.request.user
        containers = Container.objects.filter(user = user)
        return containers



@login_required
def open(request, pk, pkView):
    """Opens a container"""
    user = request.user
    container = Container.objects.filter(id = pk, user = user).first()
    if not container:
        return redirect('container:list')
    if container.state in [ Container.State.RUNNING, Container.State.NEED_RESTART ]:
        return container.redirect(pkView)
    else:
        messages.error(request, f'Cannot open {container.name} of state {container.state}')
    return redirect('container:list')

