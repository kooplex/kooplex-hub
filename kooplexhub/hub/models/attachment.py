import logging

from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import pre_save, pre_delete #, post_save, post_delete
from django.dispatch import receiver

from kooplex.settings import KOOPLEX

from .image import Image
from .service import Service

logger = logging.getLogger(__name__)

class Attachment(models.Model):
    name = models.CharField(max_length = 32, null = False, unique = True)
    creator = models.ForeignKey(User, null = False)
    description = models.TextField(max_length = 1024, null = False)
    folder = models.CharField(max_length = 32, null = False, unique = True)

    def __str__(self):
        return f"<attachment {self.name} creator: {self.creator.username}>"

class AttachmentImageBinding(models.Model):
    attachment = models.ForeignKey(Attachment, null = False)
    image = models.ForeignKey(Image, null = False)


class AttachmentServiceBinding(models.Model):
    attachment = models.ForeignKey(Attachment, null = False)
    service = models.ForeignKey(Service, null = False)


@receiver(pre_save, sender = Attachment)
def mkdir_attachment(sender, instance, **kwargs):
    from kooplex.lib.filesystem import mkdir_attachment
    if instance.id is None:
        mkdir_attachment(instance)

@receiver(pre_delete, sender = Attachment)
def garbage_attachment(sender, instance, **kwargs):
    from kooplex.lib.filesystem import garbage_attachment
    garbage_attachment(instance)

@receiver(pre_delete, sender = AttachmentServiceBinding)
def mark_service_restart(sender, instance, **kwargs):
    instance.service.mark_restart(f"attachment {instance.attachment.name} has been removed")


#FIXME: atgondolni, hogy mi mivel kompatibilis vagy ajanlas
#@receiver(pre_save, sender = AttachmentServiceBinding)
#def assert_attachment(sender, instance, **kwargs):
#    AttachmentImageBinding.objects.get(attachment = instance.attachment, image = instance.service.image)
