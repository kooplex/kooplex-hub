import logging

from django.db import models
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from ..models import VolumeContainerBinding

logger = logging.getLogger(__name__)


@receiver(post_save, sender = VolumeContainerBinding)
def restartrequired_create(sender, instance, created, **kwargs):
    if created:
        instance.container.mark_restart(reason = "volume {} needs to be mounted".format(instance.volume))


@receiver(post_delete, sender = VolumeContainerBinding)
def restartrequired_delete(sender, instance, **kwargs):
    instance.container.mark_restart(reason = "volume {} needs to be unmounted".format(instance.volume))


