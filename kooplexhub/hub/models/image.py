import logging

from django.db import models

from kooplex.settings import KOOPLEX

logger = logging.getLogger(__name__)

class Image(models.Model):
    name = models.CharField(max_length = 32)
    present = models.BooleanField(default = True)
    require_home = models.BooleanField(default = True)
    mount_report = models.BooleanField(default = True)
    mount_project = models.BooleanField(default = True)
    description = models.CharField(max_length = 250, default="description missing")

    def __str__(self):
        return self.name

    @property
    def imagename(self):
        return KOOPLEX.get('docker', {}).get('pattern_imagename', 'image-%(imagename)s') % { 'imagename': self.name }

