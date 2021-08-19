import logging

from django.db import models

from .image import Image

logger = logging.getLogger(__name__)

class EnvVarMapping(models.Model):
    image = models.ForeignKey(Image, null = False, on_delete = models.CASCADE)
    name = models.CharField(max_length = 32)
    valuemap = models.CharField(max_length = 64)

    def __str__(self):
        return f"<EnvVar {self.name}={self.valuemap}"

