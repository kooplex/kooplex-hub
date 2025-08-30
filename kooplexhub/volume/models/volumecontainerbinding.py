import logging

from django.contrib.auth.models import User
from django.db import models

from container.models import Container
from volume.models import Volume

logger = logging.getLogger(__name__)


class VolumeContainerBinding(models.Model):
    volume = models.ForeignKey(Volume, on_delete = models.CASCADE, related_name = 'containerbindings')
    container = models.ForeignKey(Container, on_delete = models.CASCADE, related_name = 'volumebindings')

    class Meta:
        unique_together = [['volume', 'container']]
