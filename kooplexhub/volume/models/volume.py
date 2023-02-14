import logging
import re
import os

from django.db import models

from kooplexhub.lib import my_alphanumeric_validator

logger = logging.getLogger(__name__)

class Volume(models.Model):
    SCP_PUBLIC = 'public'
    SCP_INTERNAL = 'internal'
    SCP_PRIVATE = 'private'
    SCP_ATTACHMENT = 'attachment'
    SCP_LOOKUP = {
        SCP_PRIVATE: 'Owner can invite collaborators to use this volume.',
        SCP_INTERNAL: 'Users in specific groups can list and may mount this volume.',
        SCP_PUBLIC: 'Authenticated users can list and may mount this volume.',
        SCP_ATTACHMENT: 'Users can create, list and may mount attachments.',
    }

    folder = models.CharField(max_length = 64, validators = [ my_alphanumeric_validator('Enter a clean volume name containing only letters and numbers.') ])
    description = models.TextField(null = True)
    claim = models.CharField(max_length = 64)
    subPath = models.CharField(max_length = 64, default = "", blank = True)
    scope = models.CharField(max_length = 16, choices = SCP_LOOKUP.items(), default = SCP_PRIVATE)
    is_present = models.BooleanField(default = True)

    class Meta:
        unique_together = [['claim', 'folder']]

    def __str__(self):
        return "Volume /{} ({}:{})".format(self.folder, self.claim, self.subPath)

    @property
    def search(self):
        return f"{self.folder} {self.description}".upper()

    @property
    def owner(self):
        from .uservolumebinding import UserVolumeBinding
        try:
            return UserVolumeBinding.objects.get(volume = self, role = UserVolumeBinding.RL_OWNER).user
        except:
            logger.error(f"Volume {self} has no owner")
            return "MISSING"

#    @property
#    def admins(self):
#        from .uservolumebinding import UserVolumeBinding
#        return [ b.user for b in UserVolumeBinding.objects.filter(volume = self, role__in = [ UserVolumeBinding.RL_OWNER, UserVolumeBinding.RL_ADMIN ]) ]

    def is_admin(self, user):
        from .uservolumebinding import UserVolumeBinding
        try:
            return UserVolumeBinding.objects.get(volume = self, user = user).role in [ UserVolumeBinding.RL_OWNER, UserVolumeBinding.RL_ADMIN ]
        except UserVolumeBinding.DoesNotExist:
            return False

    def authorize(self, user):
        from .uservolumebinding import UserVolumeBinding
        if self.scope in [ self.SCP_ATTACHMENT, self.SCP_PUBLIC ]:
            return self
        else:
            #FIXME: how to authorize internal volume?
            try:
                UserVolumeBinding.objects.get(user = user, volume = self)
                return self
            except:
                pass

    def is_user_authorized(self, user):
        from .uservolumebinding import UserVolumeBinding
        try:
            UserVolumeBinding.objects.get(user = user, volume = self)
            return True
        except UserVolumeBinding.DoesNotExist:
            return False



#    def is_collaborator(self, user):
#        from .uservolumebinding import UserVolumeBinding
#        try:
#            return UserVolumeBinding.objects.get(volume = self, user = user).role == UserVolumeBinding.RL_COLLABORATOR
#        except UserVolumeBinding.DoesNotExist:
#            return False
#
#    @property
#    def collaborators(self):
#        from .uservolumebinding import UserVolumeBinding
#        return [ b.user for b in UserVolumeBinding.objects.filter(volume = self) ]
#
##FIXME:
#    @staticmethod
#    def get_uservolume(volume_id, user):
#        from .uservolumebinding import UserVolumeBinding
#        return UserVolumeBinding.objects.get(user = user, volume_id = volume_id).volume
#
#    @staticmethod
#    def get_uservolumes(user):
#        from .uservolumebinding import UserVolumeBinding
#        return [ upb.volume for upb in UserVolumeBinding.objects.filter(user = user) ]
