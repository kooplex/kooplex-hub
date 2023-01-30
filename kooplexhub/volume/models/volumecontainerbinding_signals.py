import logging

from django.db import models
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from ..models import VolumeContainerBinding

logger = logging.getLogger(__name__)


@receiver(post_save, sender = VolumeContainerBinding)
def restartrequired_create(sender, instance, created, **kwargs):
    if created:
        t = 'attachment' if instance.volume.scope == instance.volume.SCP_ATTACHMENT else 'volume'
        instance.container.mark_restart(reason = f"{t} {instance.volume.folder} needs to be mounted")


@receiver(post_delete, sender = VolumeContainerBinding)
def restartrequired_delete(sender, instance, **kwargs):
    t = 'attachment' if instance.volume.scope == instance.volume.SCP_ATTACHMENT else 'volume'
    instance.container.mark_restart(reason = f"{t} {instance.volume.folder} needs to be unmounted")


