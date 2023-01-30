#DEPRECATED import logging
#DEPRECATED 
#DEPRECATED from django.contrib.auth.models import User
#DEPRECATED from django.db import models
#DEPRECATED from django.db.models.signals import pre_save, pre_delete #, post_save, post_delete
#DEPRECATED from django.dispatch import receiver
#DEPRECATED 
#DEPRECATED from .image import Image
#DEPRECATED from .container import Container
#DEPRECATED 
#DEPRECATED logger = logging.getLogger(__name__)
#DEPRECATED 
#DEPRECATED class Attachment(models.Model):
#DEPRECATED     name = models.CharField(max_length = 32, null = False, unique = True)
#DEPRECATED     creator = models.ForeignKey(User, on_delete = models.CASCADE, null = False)
#DEPRECATED     description = models.TextField(max_length = 1024, null = False)
#DEPRECATED     folder = models.CharField(max_length = 32, null = False, unique = True)
#DEPRECATED 
#DEPRECATED     def __str__(self):
#DEPRECATED         return f"<attachment {self.name} creator: {self.creator.username}>"
#DEPRECATED 
#DEPRECATED class AttachmentImageBinding(models.Model):
#DEPRECATED     attachment = models.ForeignKey(Attachment, on_delete = models.CASCADE, null = False)
#DEPRECATED     image = models.ForeignKey(Image, on_delete = models.CASCADE, null = False)
#DEPRECATED 
#DEPRECATED 
#DEPRECATED class AttachmentContainerBinding(models.Model):
#DEPRECATED     attachment = models.ForeignKey(Attachment, on_delete = models.CASCADE, null = False)
#DEPRECATED     container = models.ForeignKey(Container, on_delete = models.CASCADE, null = False)


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
