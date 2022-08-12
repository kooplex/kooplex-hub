import logging

from django.db import models
from django.contrib.auth.models import User

from ..models import Volume

logger = logging.getLogger(__name__)

class UserVolumeBinding(models.Model):
    RL_OWNER = 'owner'
    RL_ADMIN = 'administrator'
    RL_COLLABORATOR = 'member'
    RL_LOOKUP = {
        RL_OWNER: 'The owner of this volume.',
        RL_ADMIN: 'Can modify volume properties.',
        RL_COLLABORATOR: 'User can mount this volume read-only.',
    }
    ROLE_LIST = [ RL_OWNER, RL_ADMIN, RL_COLLABORATOR ]

    user = models.ForeignKey(User, on_delete = models.CASCADE, null = False)
    volume = models.ForeignKey(Volume, on_delete = models.CASCADE, null = False)
#    is_hidden = models.BooleanField(default = False)
    role = models.CharField(max_length = 16, choices = RL_LOOKUP.items(), null = False)

    class Meta:
        unique_together = [['user', 'volume']]

    def __str__(self):
       return "%s-%s" % (self.volume.name, self.user.username)

    @property
    def uniquename(self):#FIXME: deprecate
        return "%s-%s" % (self.volume.uniquename, self.user.username)

#    @property
#    def groupname(self):
#        return f"p-{self.volume.subpath}"

    def volumecontainerbindings(self):
        from ..models import VolumeContainerBinding
        return VolumeContainerBinding.objects.filter(volume = self.volume, container__user = self.user)

    @property
    def is_admin(self):
        return self.role in [ self.RL_ADMIN, self.RL_OWNER ]


