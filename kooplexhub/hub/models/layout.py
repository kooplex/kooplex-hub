import logging

from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User

logger = logging.getLogger(__name__)

class Layout(models.Model):
    user = models.OneToOneField(User, on_delete = models.CASCADE)
    project_list = models.BooleanField(default = True)
    service_list = models.BooleanField(default = True)
    report_list = models.BooleanField(default = True)

@receiver(post_save, sender = User)
def create_user_layout(sender, instance, created, **kwargs):
    try:
        Layout.objects.get(user = instance)
    except Layout.DoesNotExist:
        Layout.objects.create(user = instance)
        logger.info(f"New layout record for user {instance}")

