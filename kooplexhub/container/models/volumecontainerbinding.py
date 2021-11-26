import logging

from django.contrib.auth.models import User
from django.db import models

from ..models import Container
from volume.models import Volume

logger = logging.getLogger(__name__)


class VolumeContainerBinding(models.Model):
    volume = models.ForeignKey(Volume, on_delete = models.CASCADE, null = False)
    container = models.ForeignKey(Container, on_delete = models.CASCADE, null = False)

    class Meta:
        unique_together = [['volume', 'container']]
