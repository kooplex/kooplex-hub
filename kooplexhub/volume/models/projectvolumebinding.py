import logging

from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

logger = logging.getLogger(__name__)

class ProjectVolumeBinding(models.Model):
    project = models.ForeignKey('project.Project', on_delete = models.CASCADE, related_name='volumebindings')
    volume = models.ForeignKey('volume.Volume', on_delete = models.CASCADE, related_name='projectbindings')

    class Meta:
        unique_together = [['project', 'volume']]

    def __str__(self):
       return "%s-%s" % (self.project.name, self.volume.folder)

