import logging

from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

logger = logging.getLogger(__name__)

class UserProjectBinding(models.Model):
    class Role(models.TextChoices):
        CREATOR = 'creator', 'The creator of this project.'
        ADMIN = 'administrator', 'Can modify project properties.'
        COLLABORATOR = 'member', 'Member of this project.'

    user = models.ForeignKey(User, on_delete = models.CASCADE)
    project = models.ForeignKey('project.Project', on_delete = models.CASCADE, related_name = 'userbindings')
    is_hidden = models.BooleanField(default = False)
    role = models.CharField(max_length = 16, choices = Role.choices)

    class Meta:
        unique_together = [['user', 'project']]

    def __str__(self):
       return "%s-%s" % (self.project.name, self.user.username)

    @property
    def uniquename(self):#FIXME: deprecate
        return "%s-%s" % (self.project.uniquename, self.user.username)

    @property
    def groupname(self):
        return f"p-{self.project.subpath}"

    @property
    def containers(self):
        return { 
            b.container
            for b in self.project.containerbindings
                .filter(project = self.project, container__user = self.user)
                .select_related('container')
                }

    @property
    def is_admin(self):
        return self.role in [ self.Role.ADMIN, self.Role.CREATOR ]


