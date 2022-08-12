from django.dispatch import receiver
from django.db.models.signals import pre_save, post_save, post_delete, pre_delete
from . import Report
from ..filesystem import publish, remove

@receiver(post_save, sender = Report)
def publish_report(sender, instance, **kwargs):
    publish(instance)


@receiver(pre_delete, sender = Report)
def remove_report(sender, instance, **kwargs):
    remove(instance)
