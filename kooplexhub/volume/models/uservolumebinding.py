import logging

from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

logger = logging.getLogger(__name__)

class UserVolumeBinding(models.Model):
    class Role(models.TextChoices):
        OWNER = 'owner', 'The owner of this volume.'
        ADMIN = 'administrator', 'Can modify volume properties.'
        COLLABORATOR = 'member', 'User can mount this volume read-only.'

    user = models.ForeignKey(User, on_delete = models.CASCADE)
    volume = models.ForeignKey('volume.Volume', on_delete = models.CASCADE, related_name = 'userbindings')
    role = models.CharField(max_length = 16, choices = Role.choices)

    class Meta:
        unique_together = [['user', 'volume']]

    def __str__(self):
        return "Binding: {} -- {}".format(self.volume, self.user)


    def volumecontainerbindings(self):
        from ..models import VolumeContainerBinding
        return VolumeContainerBinding.objects.filter(volume = self.volume, container__user = self.user)

    @property
    def is_admin(self):
        return self.role in [ self.Role.ADMIN, self.Role.OWNER ]


