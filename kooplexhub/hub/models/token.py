import logging
import unidecode

from django.db import models
from django.contrib.auth.models import User

logger = logging.getLogger(__name__)

class Token(models.Model):
    user = models.ForeignKey(User, on_delete = models.CASCADE)
    name = models.CharField(max_length = 64, null = True)
    value = models.CharField(max_length = 512, null = True)















