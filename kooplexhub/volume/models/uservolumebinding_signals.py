import json
import logging

from django.db import transaction
from django.db.models.signals import pre_save, post_save, pre_delete, post_delete
from django.dispatch import receiver

from kooplexhub.lib.libbase import standardize_str
#FIXMEfrom hub.models import FilesystemTask, Group, UserGroupBinding
from hub.models import Group, UserGroupBinding
from ..models import UserVolumeBinding, Volume
from .. import filesystem as fs
from hub.lib.filesystem import _mkdir, _grantaccess

logger = logging.getLogger(__name__)

#code = lambda x: json.dumps([ i.id for i in x ])

@receiver(pre_save, sender = Volume)
def mkdir_attachment(sender, instance, **kwargs):
    if instance.id is None and instance.scope == instance.SCP_ATTACHMENT:
        _mkdir( fs.folder_attachment(instance) )


@receiver(pre_save, sender = UserVolumeBinding)
def grantaccess_volume(sender, instance, **kwargs):
    if instance.id is None:
        if instance.role in [ instance.RL_OWNER, instance.RL_ADMIN ]:
            if instance.volume == instance.volume.SCP_ATTACHMENT:
                _grantaccess(instance.user, fs.folder_attachment(instance.volume), recursive = True)
            else:
                pass
            #FIXME: volume access
        #FIXME: _grantgroupaccess(instance.user fs.folder_attachment(instance.volume))
        else:
            if instance.volume == instance.volume.SCP_ATTACHMENT:
                _grantaccess(instance.user, fs.folder_attachment(instance.volume), readonly = True, recursive = True)
            else:
                pass
            #FIXME: volume access
 

@receiver(pre_delete, sender = Volume)
def garbage_attachment(sender, instance, **kwargs):
    from ..filesystem import garbage_attachment
    if instance.scope == Volume.SCP_ATTACHMENT:
        fs.garbage_attachment(instance)


#@receiver(pre_save, sender = UserVolumeBinding)
#def assert_single_creator(sender, instance, **kwargs):
#    p = instance.volume
#    try:
#        upb = UserVolumeBinding.objects.get(volume = p, role = UserVolumeBinding.RL_CREATOR)
#        if instance.role == UserVolumeBinding.RL_CREATOR:
#            assert upb.id == instance.id, "Volume %s cannot have more than one creator" % p
#    except UserVolumeBinding.DoesNotExist:
#        assert instance.role == UserVolumeBinding.RL_CREATOR, "The first user volume binding must be the creator %s" % instance
#
#
#
#@receiver(pre_save, sender = UserVolumeBinding)
#def mkdir_volume(sender, instance, **kwargs):
#    p = instance.volume
#    if instance.id is None:
#        cleanname = standardize_str(p.name)
#        if p.subpath is None:
#            p.subpath = f'{cleanname}-{instance.user.username}'
#            p.save()
#        is_creator = instance.role == UserVolumeBinding.RL_CREATOR
#        if not is_creator:
#            with transaction.atomic():
#                group, group_created = Group.objects.select_for_update().get_or_create(name = instance.groupname, grouptype = Group.TP_PROJECT)
#            if group_created:
#                creator = UserVolumeBinding.objects.get(volume = instance.volume, role = UserVolumeBinding.RL_CREATOR).user
#                UserGroupBinding.objects.create(user = creator, group = group)
#                acl = { 'groups_rw': code([group]) }
#            else:
#                acl = None
#            UserGroupBinding.objects.create(user = instance.user, group = group)
#        else:
#            acl = { 'users_rw': code([instance.user]) }
#        if acl:
#            FilesystemTask.objects.create(
#                folder = fs.path_volume(p),
#                create_folder = is_creator,
#                task = FilesystemTask.TSK_GRANT,
#                **acl
#            )
#            FilesystemTask.objects.create(
#                folder = fs.path_report_prepare(p),
#                create_folder = is_creator,
#                task = FilesystemTask.TSK_GRANT,
#                **acl
#            )
#       
#
#@receiver(pre_delete, sender = UserVolumeBinding)
#def revokeaccess_volume(sender, instance, **kwargs):
#    if instance.role != UserVolumeBinding.RL_CREATOR:
#        group = Group.objects.get(name = instance.groupname, grouptype = Group.TP_PROJECT)
#        UserGroupBinding.objects.get(user = instance.user, group = group).delete()
#        FilesystemTask.objects.create(
#            folder = fs.path_volume(instance.volume),
#            users_rw = code([instance.user]),
#            task = FilesystemTask.TSK_REVOKE
#        )
#        FilesystemTask.objects.create(
#            folder = fs.path_report_prepare(instance.volume),
#            users_rw = code([instance.user]),
#            task = FilesystemTask.TSK_REVOKE
#        )


#@receiver(pre_delete, sender = UserVolumeBinding)
#def garbagedir_volume(sender, instance, **kwargs):
#    if instance.role == UserVolumeBinding.RL_CREATOR:
#        try:
#            Group.objects.get(name = instance.groupname, grouptype = Group.TP_PROJECT).delete()
#        except Group.DoesNotExist:
#            pass
#        FilesystemTask.objects.create(
#            folder = fs.path_volume(instance.volume),
#            tarbal = fs.garbage_volume(instance.volume),
#            remove_folder = True,
#            task = FilesystemTask.TSK_TAR
#        )
#        FilesystemTask.objects.create(
#            folder = fs.path_report_prepare(instance.volume),
#            remove_folder = True,
#            task = FilesystemTask.TSK_REMOVE
#        )


@receiver(pre_delete, sender = UserVolumeBinding)
def assert_not_shared(sender, instance, **kwargs):
    from ..models import VolumeContainerBinding
    for pcb in VolumeContainerBinding.objects.filter(volume = instance.volume, container__user = instance.user):
        pcb.container.mark_restart(f"Revoked access to volume {instance.volume.name}")
        pcb.delete()

