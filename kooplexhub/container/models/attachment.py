import logging

from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import pre_save, pre_delete #, post_save, post_delete
from django.dispatch import receiver

from .image import Image
from .container import Container

logger = logging.getLogger(__name__)

class Attachment(models.Model):
    name = models.CharField(max_length = 32, null = False, unique = True)
    creator = models.ForeignKey(User, on_delete = models.CASCADE, null = False)
    description = models.TextField(max_length = 1024, null = False)
    folder = models.CharField(max_length = 32, null = False, unique = True)

    def __str__(self):
        return f"<attachment {self.name} creator: {self.creator.username}>"

class AttachmentImageBinding(models.Model):
    attachment = models.ForeignKey(Attachment, on_delete = models.CASCADE, null = False)
    image = models.ForeignKey(Image, on_delete = models.CASCADE, null = False)


class AttachmentContainerBinding(models.Model):
    attachment = models.ForeignKey(Attachment, on_delete = models.CASCADE, null = False)
    container = models.ForeignKey(Container, on_delete = models.CASCADE, null = False)


#FIXME:    @receiver(pre_save, sender = Attachment)
#FIXME:    def mkdir_attachment(sender, instance, **kwargs):
#FIXME:        from kooplex.lib.filesystem import mkdir_attachment
#FIXME:        if instance.id is None:
#FIXME:            mkdir_attachment(instance)
#FIXME:    
#FIXME:    @receiver(pre_delete, sender = Attachment)
#FIXME:    def garbage_attachment(sender, instance, **kwargs):
#FIXME:        from kooplex.lib.filesystem import garbage_attachment
#FIXME:        garbage_attachment(instance)
#FIXME:    
#FIXME:    @receiver(pre_delete, sender = AttachmentServiceBinding)
#FIXME:    def mark_service_restart(sender, instance, **kwargs):
#FIXME:        instance.service.mark_restart(f"attachment {instance.attachment.name} has been removed")


#FIXME: atgondolni, hogy mi mivel kompatibilis vagy ajanlas
#@receiver(pre_save, sender = AttachmentServiceBinding)
#def assert_attachment(sender, instance, **kwargs):
#    AttachmentImageBinding.objects.get(attachment = instance.attachment, image = instance.service.image)
