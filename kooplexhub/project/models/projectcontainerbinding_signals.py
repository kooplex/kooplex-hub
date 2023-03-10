import logging

from django.db import models
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from ..models import ProjectContainerBinding

logger = logging.getLogger(__name__)


@receiver(post_save, sender = ProjectContainerBinding)
def restartrequired_create(sender, instance, created, **kwargs):
    if created:
        instance.container.mark_restart(reason = f"Project folders {instance.project.subpath} needs to be mounted")


@receiver(post_delete, sender = ProjectContainerBinding)
def restartrequired_delete(sender, instance, **kwargs):
    instance.container.mark_restart(reason = f"Project folders {instance.project.subpath} needs to be unmounted")


