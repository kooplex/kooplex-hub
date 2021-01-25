import logging

from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User

logger = logging.getLogger(__name__)

class Search(models.Model):
    user = models.OneToOneField(User, on_delete = models.CASCADE)

    project_list = models.CharField(max_length = 30, blank = True, null = True, default = "")
    project_join = models.CharField(max_length = 30, blank = True, null = True, default = "")
    project_showhide = models.CharField(max_length = 30, blank = True, null = True, default = "")
    project_collaborator = models.CharField(max_length = 30, blank = True, null = True, default = "")
    project_service = models.CharField(max_length = 30, blank = True, null = True, default = "")

    service_list = models.CharField(max_length = 30, blank = True, null = True, default = "")
    service_projects = models.CharField(max_length = 30, blank = True, null = True, default = "")
    service_library = models.CharField(max_length = 30, blank = True, null = True, default = "")

    report_list = models.CharField(max_length = 30, blank = True, null = True, default = "")

    external_library = models.CharField(max_length = 30, blank = True, null = True, default = "")
    external_repository = models.CharField(max_length = 30, blank = True, null = True, default = "")

@receiver(post_save, sender = User)
def create_user_search(sender, instance, created, **kwargs):
    try:
        Search.objects.get(user = instance)
    except Search.DoesNotExist:
        Search.objects.create(user = instance)
        logger.info(f"New search record for user {instance}")

