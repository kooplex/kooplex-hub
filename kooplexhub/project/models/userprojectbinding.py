import logging

from django.db import models
from django.contrib.auth.models import User

from ..models import Project

logger = logging.getLogger(__name__)

class UserProjectBinding(models.Model):
    RL_CREATOR = 'creator'
    RL_ADMIN = 'administrator'
    RL_COLLABORATOR = 'member'
    RL_LOOKUP = {
        RL_CREATOR: 'The creator of this project.',
        RL_ADMIN: 'Can modify project properties.',
        RL_COLLABORATOR: 'Member of this project.',
    }
    ROLE_LIST = [ RL_CREATOR, RL_ADMIN, RL_COLLABORATOR ]

    user = models.ForeignKey(User, on_delete = models.CASCADE, null = False)
    project = models.ForeignKey(Project, on_delete = models.CASCADE, null = False)
    is_hidden = models.BooleanField(default = False)
    role = models.CharField(max_length = 16, choices = RL_LOOKUP.items(), null = False)

    class Meta:
        unique_together = [['user', 'project']]

    def __str__(self):
       return "%s-%s" % (self.project.name, self.user.username)

    @property
    def uniquename(self):
        return "%s-%s" % (self.project.uniquename, self.user.username)

    def projectcontainerbindings(self):
        from ..models import ProjectContainerBinding
        return ProjectContainerBinding.objects.filter(project = self.project, container__user = self.user)

    @property
    def is_admin(self):
        return self.role in [ self.RL_ADMIN, self.RL_CREATOR ]


