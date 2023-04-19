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

from api.kube import save_token

@receiver(post_save, sender = Profile)
def kube_save_token(sender, instance, created, **kwargs):
    if instance.is_superuser:
        logger.debug("Admin user %s" % instance)
        return
    save_token(namespace=KOOPLEX.get('kubernetes', {}).get('namespace', 'default'), user=instance.user.username, token=instance.token)
