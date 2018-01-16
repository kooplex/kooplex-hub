from django.db import models

from .user import User
from .image import Image
from .scope import ScopeType

class Project(models.Model):
    id = models.AutoField(primary_key = True)
    name = models.TextField(max_length = 200, null = False)
    description = models.TextField(null=True)
    owner = models.ForeignKey(User, null = True)
    image = models.ForeignKey(Image, null = True)
    scope = models.ForeignKey(ScopeType, null = True)

    def __lt__(self, p):
        return self.name < p.name

    def __str__(self):
        return "%s@%s" % (self.name, self.owner)

    @property
    def name_with_owner(self):
        return "%s-%s" % (self.name, self.owner.username)

    @property
    def collaborators(self):
        for upb in UserProjectBinding.objects.filter(project = self):
            yield upb.user

    @property
    def volumes(self):
        from .volume import VolumeProjectBinding
        for vpb in VolumeProjectBinding.objects.filter(project = self):
            yield vpb.volume

#FIXME: add mountpoint iterator
          
class UserProjectBinding(models.Model):
    id = models.AutoField(primary_key = True)
    user = models.ForeignKey(User, null = False)
    project = models.ForeignKey(Project, null = False)

    def __str__(self):
       return "%s-%s" % (self.project.name, self.user.username)

