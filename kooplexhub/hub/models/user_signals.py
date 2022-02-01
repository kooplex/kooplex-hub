import logging
import pwgen

from django.contrib.auth.models import User
from django.dispatch import receiver
from django.db.models.signals import post_save, pre_delete, post_delete

from kooplexhub.settings import KOOPLEX

from ..lib import filename, dirname
from ..models import Profile, FilesystemTask

logger = logging.getLogger(__name__)

@receiver(post_save, sender = User)
def user_creation(sender, instance, created, **kwargs):
    if instance.is_superuser:
        logger.debug("Admin user %s" % instance)
        return
    if created or not hasattr(instance, 'profile'):
        logger.info("New user %s" % instance)
        token = pwgen.pwgen(64)
        Profile.objects.create(user = instance, token = token)
    FilesystemTask.objects.create(
        folder = dirname.userhome(instance),
        grantee_user = instance,
        create_folder = True,
        task = FilesystemTask.TSK_GRANT_USER
    )
    FilesystemTask.objects.create(
        folder = dirname.usergarbage(instance),
        grantee_user = instance,
        create_folder = True,
        task = FilesystemTask.TSK_GRANT_USER
    )
    if KOOPLEX.get('mountpoint_hub', {}).get('scratch') is not None:
        FilesystemTask.objects.create(
            folder = dirname.userscratch(instance),
            grantee_user = instance,
            create_folder = True,
            task = FilesystemTask.TSK_GRANT_USER
        )


@receiver(pre_delete, sender = User)
def garbage_user_home(sender, instance, **kwargs):
    if KOOPLEX.get('mountpoint_hub', {}).get('scratch') is not None:
        FilesystemTask.objects.create(
            folder = dirname.userscratch(instance),
            remove_folder = True,
            task = FilesystemTask.TSK_REMOVE
        )
    FilesystemTask.objects.create(
        folder = dirname.usergarbage(instance),
        remove_folder = True,
        task = FilesystemTask.TSK_REMOVE
    )
    if KOOPLEX.get('archive_home'):
        FilesystemTask.objects.create(
            folder = dirname.userhome(instance),
            tarbal = filename.userhome_garbage(instance),
            remove_folder = True,
            task = FilesystemTask.TSK_TAR
        )
    else:
        FilesystemTask.objects.create(
            folder = dirname.userhome(instance),
            remove_folder = True,
            task = FilesystemTask.TSK_REMOVE
        )


