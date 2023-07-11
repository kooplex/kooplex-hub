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

from api.kube import get_or_create_empty_user_secret, update_user_secret

@receiver(post_save, sender = Profile)
def kube_create_token(sender, instance, created, **kwargs):
    # FIX_BUG
    try:
        if instance.is_superuser:
            logger.debug("Admin user %s" % instance)
            return
    except:
        pass

    get_or_create_empty_user_secret(user=instance.user)
    # FIXME
    # job token to access jobs api
    token = {'job_token': instance.token}
    update_user_secret(user=instance.user, token=token)

