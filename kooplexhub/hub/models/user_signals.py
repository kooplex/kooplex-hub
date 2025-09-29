import logging
import pwgen
import json

from django.contrib.auth.models import User
from django.dispatch import receiver
from django.db.models.signals import post_save, pre_delete, post_delete

from hub.models import *
from hub.lib import mkdir, grantaccess_user
from hub.fs import userhome, usergarbage, userscratch

from ..conf import HUB_SETTINGS

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
        userdirs = [ userhome, usergarbage ]
        if HUB_SETTINGS["mounts"]["scratch"]:
            userdirs.append(userscratch)
        for userdir in userdirs:
            folder = userdir(instance)
            mkdir(folder)
            grantaccess_user(instance, folder, readonly = False, recursive = True)
    

@receiver(pre_delete, sender = User)
def garbage_user_home(sender, instance, **kwargs):
    from hub.tasks import garbage_home
    garbage_home(instance.id)


