import logging

from django.db import models
from django.contrib.auth.models import User

from ..models import Volume
from project.models import Project

logger = logging.getLogger(__name__)

class ProjectVolumeBinding(models.Model):

    project = models.ForeignKey(Project, on_delete = models.CASCADE, null = False)
    volume = models.ForeignKey(Volume, on_delete = models.CASCADE, null = False)

    class Meta:
        unique_together = [['project', 'volume']]

    def __str__(self):
       return "%s-%s" % (self.project.name, self.volume.username)

    @property
    def uniquename(self):#FIXME: deprecate
        return "%s-%s" % (self.project.uniquename, self.volume.username)

#    @property
#    def groupname(self):
#        return f"p-{self.volume.subpath}"

#    def volumecontainerbindings(self):
#        from container.models import VolumeContainerBinding
#        return VolumeContainerBinding.objects.filter(volume = self.volume, container__user = self.user)


