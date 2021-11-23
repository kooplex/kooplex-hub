import logging
import pwgen

from django.contrib.auth.models import User
from django.dispatch import receiver
from django.db.models.signals import post_save, pre_delete, post_delete

from ..models import Profile

logger = logging.getLogger(__name__)

@receiver(post_save, sender = User)
def user_creation(sender, instance, created, **kwargs):
    from kooplexhub.lib import mkdir_home, mkdir_scratch
    if created or not hasattr(instance, 'profile'):
        logger.info("New user %s" % instance)
        token = pwgen.pwgen(64)
        #FIXME: exclude admins!
        Profile.objects.create(user = instance, token = token)
    try:
        mkdir_home(instance)
    except Exception as e:
        logger.error("Failed to create home for %s -- %s" % (instance, e))
    try:
        mkdir_scratch(instance)
    except Exception as e:
        logger.error("Failed to create scratch for %s -- %s" % (instance, e))


#FIXME: @receiver(pre_delete, sender = User)
#FIXME: def garbage_user_home(sender, instance, **kwargs):
#FIXME:     from kooplex.lib.filesystem import garbagedir_home
#FIXME:     garbagedir_home(instance)




