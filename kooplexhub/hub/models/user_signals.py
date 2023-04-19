import logging
import pwgen
import json

from django.contrib.auth.models import User
from django.dispatch import receiver
from django.db.models.signals import post_save, pre_delete, post_delete

from hub.models import * #Profile, Task
from hub.lib import filename, dirname
from hub.lib import mkdir, grantaccess_user

try:
    from kooplexhub.settings import KOOPLEX
except ImportError:
    KOOPLEX = {}

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
        userdirs = [ dirname.userhome, dirname.usergarbage ]
        if KOOPLEX.get('mountpoint_hub', {}).get('scratch') is not None:
            userdirs.append(dirname.userscratch)
        for userdir in userdirs:
            folder = userdir(instance)
            mkdir(folder)
            grantaccess_user(instance, folder, readonly = False, recursive = True)
    

@receiver(pre_delete, sender = User)
def garbage_user_home(sender, instance, **kwargs):
    Task(
        create = True,
        name = f"Garbage home {instance.username}",
        task = "hub.tasks.garbage_home",
        kwargs = {
            'user_id': instance.id,
        }
    )


