import logging
import json

from django.shortcuts import render, redirect, reverse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views import generic
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.utils.html import format_html

from hub.templatetags.extras import manual_link

from .models import Volume, UserVolumeBinding
##from .forms import TableVolumeShare
from .forms import FormAttachment, FormVolumeUpdate

logger = logging.getLogger(__name__)

class VolumeListView(LoginRequiredMixin, generic.ListView):
    template_name = 'volume_list.html'
    context_object_name = 'volumes'
    model = Volume

    def get_context_data(self, **kwargs):
        l = manual_link(item = "volume")
        context = super().get_context_data(**kwargs)
        context['menu_storage'] = True
        context['submenu'] = 'list_volume'
        context['empty_title'] = 'No volumes available'
        context['empty_body'] = format_html(f'You do no have access to the volumes yet. Ask volume owners or volume administrators for collaboration. {l}')
        return context

    def get_queryset(self):
        user = self.request.user
        volumes = filter(lambda v: v.authorize(user), Volume.objects.all() )
        return list(volumes)


class NewAttachmentView(LoginRequiredMixin, generic.FormView):
    template_name = 'attachment_new.html'
    form_class = FormAttachment
    success_url = '/hub/volume/list' #FIXME: reverse('volume:list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['menu_storage'] = True
        context['submenu'] = 'new_attachment'
        return context

    def form_valid(self, form):
        logger.info(form.cleaned_data)
        user = self.request.user
        v = Volume.objects.create(**form.cleaned_data)
        UserVolumeBinding.objects.create(volume = v, user = user, role = UserVolumeBinding.RL_OWNER) 
        messages.info(self.request, f'Attachment {v.folder} is created')
        return super().form_valid(form)


class ConfigureVolumeView(LoginRequiredMixin, generic.edit.UpdateView):
    model = Volume
    form_class = FormVolumeUpdate
    template_name = 'volume_configure.html'
    success_url = '/hub/volume/list' #FIXME: 

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['menu_storage'] = True
        context['volume_id'] = self.kwargs['pk']
        if Volume.objects.get(id = self.kwargs['pk']).scope == Volume.SCP_ATTACHMENT:
            context['active'] = 'meta'
            context['is_attachment'] = True
        else:
            context['active'] = self.request.COOKIES.get('configure_volume_tab', 'meta')
            context['is_attachment'] = False
        return context

    def form_valid(self, form):
        logger.info(form.cleaned_data)
        shared = json.loads(form.cleaned_data['shared'])
        admins = shared['admin_users']
        bindings_rm = UserVolumeBinding.objects.filter(volume__id = form.cleaned_data['id']).exclude(user = self.request.user).exclude(id__in = shared['bindings'])
        bindings_rm.delete()
        #FIXME: revoke admin rights
        volume = Volume.objects.get(id = form.cleaned_data['id'])
        for uid in shared['bind_users']:
            role = UserVolumeBinding.RL_ADMIN if uid in admins else UserVolumeBinding.RL_COLLABORATOR
            user = User.objects.get(id = uid)
            UserVolumeBinding.objects.create(volume = volume, user = user, role = role)
        return super().form_valid(form)


