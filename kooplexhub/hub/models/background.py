import logging

from django.db import models
from django.contrib.auth.models import User

logger = logging.getLogger(__name__)

class Background(models.Model):
    user = models.ForeignKey(User, null = True, on_delete = models.CASCADE)
    function = models.CharField(max_length = 64)
    launched_at = models.DateTimeField(auto_now_add = True)
    error = models.CharField(max_length = 256, null = True, default = None)
    error_at = models.DateTimeField(null = True, default = None)

