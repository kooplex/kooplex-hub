import logging

from django.db import models
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from ..models import CourseContainerBinding

logger = logging.getLogger(__name__)


@receiver(post_save, sender = CourseContainerBinding)
def restartrequired_create(sender, instance, created, **kwargs):
    if created:
        instance.container.mark_restart(reason = f"Folders of course {instance.course.name} needs to be mounted")


@receiver(post_delete, sender = CourseContainerBinding)
def restartrequired_delete(sender, instance, **kwargs):
    instance.container.mark_restart(reason = f"Folders of course {instance.course.name} needs to be unmounted")


