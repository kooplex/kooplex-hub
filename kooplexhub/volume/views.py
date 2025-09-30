import logging
import json

from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views import generic
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.html import format_html

from hub.templatetags.extras import manual_link

from .models import Volume, UserVolumeBinding
from .forms import FormAttachment

from .conf import VOLUME_SETTINGS

logger = logging.getLogger(__name__)

class VolumeListView(LoginRequiredMixin, generic.ListView):
    template_name = 'volume/list.html'
    context_object_name = 'volumes'
    model = Volume

    def get_context_data(self, **kwargs):
        l = manual_link(item = "volume")
        context = super().get_context_data(**kwargs)
        context['menu_storage'] = True
        context['wss_volume_config'] = VOLUME_SETTINGS['wss']['config'].format(user = self.request.user)
        context['empty_title'] = 'No volumes available'
        context['empty_body'] = format_html(f'You do no have access to the volumes yet. Ask volume owners or volume administrators for collaboration. {l}')
        return context

    def get_queryset(self):
        user = self.request.user
        return Volume.objects.filter(userbindings__user=user)


class NewAttachmentView(LoginRequiredMixin, generic.FormView):
    template_name = 'volume/new.html'
    form_class = FormAttachment
    success_url = reverse_lazy('volume:list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['menu_storage'] = True
        return context

    def form_valid(self, form):
        logger.info(form.cleaned_data)
        user = self.request.user
        v = Volume.objects.create(**form.cleaned_data)
        UserVolumeBinding.objects.create(volume = v, user = user, role = UserVolumeBinding.Role.OWNER) 
        messages.info(self.request, f'Attachment {v.folder} is created')
        return super().form_valid(form)


@login_required
def destroy(request, pk):
    """Deletes an attacment instance"""
    user = request.user
    if attachment := Volume.objects.filter(id = pk, scope=Volume.Scope.ATTACHMENT, userbindings__user = user).first():
        logger.info(f'deleting {attachment}')
        attachment.delete()
        messages.info(request, f'Your attachment {attachment.folder} is deleted.')
    return redirect('volume:list')

