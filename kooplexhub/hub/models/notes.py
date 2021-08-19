import logging

from django.db import models

logger = logging.getLogger(__name__)

class Note(models.Model):
    message = models.TextField(max_length = 1024, null = False)
    created_at = models.DateTimeField(auto_now_add = True)
    is_public = models.BooleanField(default = True)
    expired = models.BooleanField(default = False)
