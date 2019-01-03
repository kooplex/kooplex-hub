import logging

from django.db import models
from django.db.models.signals import post_save, pre_delete, post_delete
from django.dispatch import receiver
from django.contrib.auth.models import User

logger = logging.getLogger(__name__)


class VCToken(models.Model):
    TP_GITHUB = 'github'
    TP_GITLAB = 'gitlab'
    TYPE_LIST = [ TP_GITHUB, TP_GITLAB ]

    user = models.ForeignKey(User, null = False)
    token = models.CharField(max_length = 256, null = False) # FIXME: dont store as clear text
    backend_type = models.CharField(max_length = 16, choices = [ (x, x) for x in TYPE_LIST ], default = TP_GITHUB)
    url = models.CharField(max_length = 128, null = True)
    error_flag = models.BooleanField(default = False)       # TODO: save error message maybe stored in a separate table
    
