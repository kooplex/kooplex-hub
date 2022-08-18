import logging

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views import generic
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User

from .models import Volume, UserVolumeBinding
from .forms import TableVolumeShare

logger = logging.getLogger(__name__)

class VolumeListView(LoginRequiredMixin, generic.ListView):
    template_name = 'volume_list.html'
    context_object_name = 'uservolumebindingslist'
    model = Volume

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['menu_storage'] = True
        context['submenu'] = 'list_volume'
        return context

    def get_queryset(self):
        user = self.request.user
        volumebindings = UserVolumeBinding.objects.filter(user = user).order_by('volume__name')
        logger.debug(f'UVB {volumebindings}')
        return volumebindings

def new(request):
    return NotImplementedError

@login_required
def delete_or_leave(request, volume_id):
    """Delete or leave a volume."""
    user = request.user
    logger.debug("method: %s, volume id: %s, user: %s" % (request.method, volume_id, user))
    try:
        volume = Volume.get_uservolume(volume_id = volume_id, user = user)
        uvb = UserVolumeBinding.objects.get(user = user, volume = volume)
    except Volume.DoesNotExist:
        messages.error(request, 'Volume does not exist')
        return redirect('volume:list')
    if uvb.role == uvb.RL_OWNER:
        collab = []
        for uvb_i in UserVolumeBinding.objects.filter(volume = volume):
            if uvb != uvb_i:
                collab.append(uvb_i.user)
                uvb_i.delete()
        try:
            uvb.delete()
            volume.delete()
            if len(collab):
                messages.info(request, 'Users removed from collaboration: {}'.format(', '.join([  f'{u.first_name} {u.last_name} ({u.username})' for u in collab ])))
            messages.info(request, 'Volume %s is deleted' % (volume))
        except Exception as e:
            messages.error(request, f'Cannot delete volume {volume.name}. Ask the administrator to solve this error {e}')
    else:
        uvb.delete()
        messages.info(request, 'You left volume %s' % (volume))
    return redirect('volume:list')

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
