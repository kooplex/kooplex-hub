import json
import logging

from django.db.models.signals import pre_save, post_save, pre_delete, post_delete
from django.dispatch import receiver

from ..models import UserVolumeBinding, Volume
from volume.fs import folder_attachment
from hub.lib.filesystem import _mkdir, _grantaccess, _rmdir

logger = logging.getLogger(__name__)

@receiver(pre_save, sender = Volume)
def mkdir_attachment(sender, instance, **kwargs):
    if instance.id is None and instance.scope == instance.Scope.ATTACHMENT:
        _mkdir( folder_attachment(instance) )
 

@receiver(pre_delete, sender = Volume)
def drop_attachment(sender, instance, **kwargs):
    if instance.scope == Volume.Scope.ATTACHMENT:
        _rmdir( folder_attachment(instance) )


@receiver(pre_save, sender = UserVolumeBinding)
def grantaccess_volume(sender, instance, **kwargs):
    if instance.id is None:
        if instance.role in [ instance.Role.OWNER, instance.Role.ADMIN ]:
            if instance.volume == instance.volume.Scope.ATTACHMENT:
                _grantaccess(instance.user, folder_attachment(instance.volume), recursive = True)
            else:
                pass
        else:
            if instance.volume == instance.volume.Scope.ATTACHMENT:
                _grantaccess(instance.user, folder_attachment(instance.volume), readonly = True, recursive = True)
            else:
                pass



@receiver(pre_delete, sender = UserVolumeBinding)
def assert_not_shared(sender, instance, **kwargs):
    qs = (
        instance.volume.containerbindings
        .select_related('container')
        .filter(container__user=instance.user)
    )
    for vcb in qs:
        vcb.container.mark_restart(f"Revoked access from volume {instance.volume.folder}")
        vcb.delete()

