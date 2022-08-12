import logging

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views import generic
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User

from .models import Volume, UserVolumeBinding
from .forms import TableCollaborator #,FormProject, TableJoinProject, , TableProjectContainer, TableContainer

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
        assert volume.is_admin(user), "You don't have the necessary rights"
        collaborator_ids_before = set(request.POST.getlist('collaborator_ids_before'))
        collaborator_ids_after = set(request.POST.getlist('collaborator_ids_after'))
        admin_ids_before = set(request.POST.getlist('admin_ids_before'))
        admin_ids_after = set(request.POST.getlist('admin_ids_after'))
        # removal
        removed = []
        collaborator_ids_to_remove = collaborator_ids_before.difference(collaborator_ids_after)
        for i in collaborator_ids_to_remove:
            b = UserVolumeBinding.objects.get(user__id = i, volume = volume)
            removed.append(b.user.username)
            b.delete()
        # addition
        added = []
        service_ids = request.POST.getlist('service_ids')
        collaborator_ids_to_add = collaborator_ids_after.difference(collaborator_ids_before)
        for i in collaborator_ids_to_add:
            collaborator = User.objects.get(id = i)
            if i in admin_ids_after:
                b = UserVolumeBinding.objects.create(user = collaborator, volume = volume, role = UserVolumeBinding.RL_ADMIN)
            else:
                b = UserVolumeBinding.objects.create(user = collaborator, volume = volume, role = UserVolumeBinding.RL_COLLABORATOR)
            added.append(b.user.username)
            # copy service information
            for sid in service_ids:
                svc = VolumeContainerBinding.objects.get(id = sid, container__user = user).container
                svc_copy = Container.objects.create(user = collaborator, image = svc.image, name = f'{b.user.username}-{volume.subpath}')
                VolumeContainerBinding.objects.create(container = svc_copy, volume = volume)
                #TODO: handle volumes and attachments
        # role change
        changed = []
        collaborator_ids_to_admin = admin_ids_after.difference(admin_ids_before).intersection(collaborator_ids_after).difference(collaborator_ids_to_add)
        collaborator_ids_to_revokeadmin = admin_ids_before.difference(admin_ids_after).intersection(collaborator_ids_after).difference(collaborator_ids_to_add)
        for i in collaborator_ids_to_admin:
            b = UserVolumeBinding.objects.filter(user__id = i, volume = volume).exclude(role = UserVolumeBinding.RL_CREATOR)
            assert len(b) == 1
            b = b[0]
            b.role = UserVolumeBinding.RL_ADMIN
            changed.append(b.user.username)
            b.save()
        for i in collaborator_ids_to_revokeadmin:
            b = UserVolumeBinding.objects.filter(user__id = i, volume = volume).exclude(role = UserVolumeBinding.RL_CREATOR)
            assert len(b) == 1
            b = b[0]
            b.role = UserVolumeBinding.RL_COLLABORATOR
            changed.append(b.user.username)
            b.save()
        if added:
            messages.info(request, 'Added {} as colaborators'.format(', '.join(added)))
        if removed:
            messages.info(request, 'Removed {} from colaboration'.format(', '.join(removed)))
        if changed:
            messages.info(request, 'Changed collaboration roles of {}'.format(', '.join(changed)))

        # service
        psb_ids_before = set(request.POST.getlist('psb_ids_before'))
        psb_ids_after = set(request.POST.getlist('psb_ids_after'))
        # removal
        removed = []
        restart = []
        psb_ids_to_remove = psb_ids_before.difference(psb_ids_after)
        for i in psb_ids_to_remove:
            b = VolumeContainerBinding.objects.get(id = i, volume = volume, container__user = user)
            svc = b.container
            removed.append(svc.name)
            if svc.mark_restart(f'volume {volume.name} removed'):
                restart.append(svc.name)
            b.delete()
        # addition
        added = []
        svc_ids = request.POST.getlist('svc_ids')
        for i in svc_ids:
            svc = Container.objects.get(id = i, user = user)
            VolumeContainerBinding.objects.create(container = svc, volume = volume)
            added.append(svc.name)
            if svc.mark_restart(f'volume {volume.name} added'):
                restart.append(svc.name)
            b.delete()
        # addition
        added = []
        svc_ids = request.POST.getlist('svc_ids')
        for i in svc_ids:
            svc = Container.objects.get(id = i, user = user)
            VolumeContainerBinding.objects.create(container = svc, volume = volume)
            added.append(svc.name)
            if svc.mark_restart(f'volume {volume.name} added'):
                restart.append(svc.name)
        if added:
            messages.info(request, 'Added service environments {0} to volume {1}'.format(', '.join(added), volume.name))
        if removed:
            messages.info(request, 'Removed service environments {0} from volume {1}'.format(', '.join(removed), volume.name))
        if restart:
            messages.warning(request, 'Restart service environments {} because they became inconsistent'.format(', '.join(restart)))

        return redirect('volume:list')
    else:
        active_tab = request.GET.get('active_tab', 'share')

        everybodyelse = user.profile.everybodyelse
        table_share = TableCollaborator(volume, everybodyelse)

        context_dict = {
            'volume': volume,
            'active': active_tab,
            't_share': table_share,
        }
        return render(request, 'volume_configure.html', context = context_dict)
