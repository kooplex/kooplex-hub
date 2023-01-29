import logging

from django.shortcuts import render, redirect, reverse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views import generic
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.utils.html import format_html

from hub.templatetags.extras import manual_link

from .models import Volume, UserVolumeBinding
from .forms import TableVolumeShare
from .forms import FormAttachment, FormAttachmentUpdate

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
        volumes = [ b.volume for b in UserVolumeBinding.objects.filter(user = user) ]
        volumes.extend( Volume.objects.filter(scope = Volume.SCP_ATTACHMENT) )
        return volumes


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


class ConfigureAttachmentView(LoginRequiredMixin, generic.edit.UpdateView):
    model = Volume
    form_class = FormAttachmentUpdate
    template_name = 'attachment_configure.html'
    success_url = '/hub/volume/list' #FIXME: 

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['menu_storage'] = True
        context['volume_id'] = self.kwargs['pk']
        return context


##REFACTORME:  @login_required
##REFACTORME:  def delete_or_leave(request, volume_id):
##REFACTORME:      """Delete or leave a volume."""
##REFACTORME:      user = request.user
##REFACTORME:      logger.debug("method: %s, volume id: %s, user: %s" % (request.method, volume_id, user))
##REFACTORME:      try:
##REFACTORME:          volume = Volume.get_uservolume(volume_id = volume_id, user = user)
##REFACTORME:          uvb = UserVolumeBinding.objects.get(user = user, volume = volume)
##REFACTORME:      except Volume.DoesNotExist:
##REFACTORME:          messages.error(request, 'Volume does not exist')
##REFACTORME:          return redirect('volume:list')
##REFACTORME:      if uvb.role == uvb.RL_OWNER:
##REFACTORME:          collab = []
##REFACTORME:          for uvb_i in UserVolumeBinding.objects.filter(volume = volume):
##REFACTORME:              if uvb != uvb_i:
##REFACTORME:                  collab.append(uvb_i.user)
##REFACTORME:                  uvb_i.delete()
##REFACTORME:          try:
##REFACTORME:              uvb.delete()
##REFACTORME:              volume.delete()
##REFACTORME:              if len(collab):
##REFACTORME:                  messages.info(request, 'Users removed from collaboration: {}'.format(', '.join([  f'{u.first_name} {u.last_name} ({u.username})' for u in collab ])))
##REFACTORME:              messages.info(request, 'Volume %s is deleted' % (volume))
##REFACTORME:          except Exception as e:
##REFACTORME:              messages.error(request, f'Cannot delete volume {volume.name}. Ask the administrator to solve this error {e}')
##REFACTORME:      else:
##REFACTORME:          uvb.delete()
##REFACTORME:          messages.info(request, 'You left volume %s' % (volume))
##REFACTORME:      return redirect('volume:list')
##REFACTORME:  
@login_required
def configure(request, volume_id):
    user = request.user
    logger.debug("method: %s, volume id: %s, user: %s" % (request.method, volume_id, user))

    if request.POST.get('button', '') == 'cancel':
        return redirect('volume:list')
    try:
        volume = Volume.get_uservolume(volume_id = volume_id, user = request.user)
    except Volume.DoesNotExist as e:
        logger.error('abuse by %s volume id: %s -- %s' % (user, volume_id, e))
        messages.error(request, 'Volume does not exist')
        return redirect('volume:list')

    if request.POST.get('button', '') == 'apply':

        # meta
        volume.scope = request.POST['volume_scope']
        volume.description = request.POST.get('description')
        volume.save()

        # collaboration
        added = []
        admins = set(map(int, request.POST.getlist('admin_id')))
        for uid in map(int, request.POST.getlist('user_id')):
            collaborator = User.objects.get(id = uid)
            UserVolumeBinding.objects.create(
                user = collaborator, volume = volume, 
                role = UserVolumeBinding.RL_ADMIN if uid in admins else UserVolumeBinding.RL_COLLABORATOR)
            added.append(f"{collaborator.first_name} {collaborator.last_name}")
        if added:
            messages.info(request, 'Collaborators {} are granted access to volume {}.'.format(', '.join(added), volume.name))
        removed = []
        for bid in map(int, request.POST.getlist('_uservolumebinding_id')):
            b = UserVolumeBinding.objects.get(id = bid, volume = volume)
            b.delete()
            collaborator = b.user
            removed.append(f"{collaborator.first_name} {collaborator.last_name}")
        if removed:
            messages.info(request, 'Collaborators {} are revoked access from volume {}.'.format(', '.join(removed), volume.name))
        granted = []
        revoked = []
        collabs_before = { b.id: b for b in UserVolumeBinding.objects.filter(volume = volume).exclude(user = user) }
        collabs_after = set(map(int, request.POST.getlist('uservolumebinding_id')))
        for bid in collabs_after.intersection(collabs_before.keys()):
            b = collabs_before[bid]
            collaborator = b.user
            if b.role == b.RL_ADMIN and not b.user.id in admins:
                b.role = b.RL_COLLABORATOR
                b.save()
                revoked.append(f"{collaborator.first_name} {collaborator.last_name}")
            elif b.role == b.RL_COLLABORATOR and b.user.id in admins:
                b.role = b.RL_ADMIN
                b.save()
                granted.append(f"{collaborator.first_name} {collaborator.last_name}")
        if granted:
            messages.info(request, 'Granted admin rights to {} for volume {}.'.format(', '.join(granted), volume.name))
        if revoked:
            messages.info(request, 'Revoked admin rights from {} to volume {}.'.format(', '.join(revoked), volume.name))
        return redirect('volume:list')
    else:
        context_dict = {
            'menu_storage': True,
            'active': request.COOKIES.get('configure_volume_tab', 'meta'),
            't_users': TableVolumeShare(volume, user, collaborator_table = False),
            't_collaborators': TableVolumeShare(volume, user, collaborator_table = True),
            'volume': volume,
        }
        return render(request, 'volume_configure.html', context = context_dict)
