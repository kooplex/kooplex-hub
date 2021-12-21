import logging
import pwgen

from django.contrib.auth.models import User
from django.dispatch import receiver
from django.db.models.signals import post_save, pre_delete, post_delete

from ..models import Profile

logger = logging.getLogger(__name__)

@receiver(post_save, sender = User)
def user_creation(sender, instance, created, **kwargs):
    from kooplexhub.lib import provision_home, provision_scratch
    #FIXME: exclude admins!
    if created or not hasattr(instance, 'profile'):
        logger.info("New user %s" % instance)
        token = pwgen.pwgen(64)
        Profile.objects.create(user = instance, token = token)
    provision_home(instance)
    provision_scratch(instance)


@receiver(pre_delete, sender = User)
def garbage_user_home(sender, instance, **kwargs):
    from kooplex.lib.filesystem import garbagedir_home
    garbagedir_home(instance)


