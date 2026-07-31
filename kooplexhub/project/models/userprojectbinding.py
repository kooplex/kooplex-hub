import logging

from django.db import models
from django.db.models import Q
from django.contrib.auth import get_user_model

User = get_user_model()
logger = logging.getLogger(__name__)


class UserProjectBinding(models.Model):
    class Role(models.TextChoices):
        CREATOR = 'creator', 'The creator of this project.'
        ADMIN = 'administrator', 'Can modify project properties.'
        COLLABORATOR = 'member', 'Member of this project.'

        @classmethod
        def assignable_choices(cls):
            return (
                (cls.ADMIN, cls.ADMIN.label),
                (cls.COLLABORATOR, cls.COLLABORATOR.label),
            )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="projectbindings",
    )

    project = models.ForeignKey(
        "project.Project",
        on_delete=models.CASCADE,
        related_name="userbindings",
    )

    is_hidden = models.BooleanField(default=False)

    role = models.CharField(
        max_length=16,
        choices=Role.choices,
    )

    class Meta:
        constraints = [
#TODO            models.UniqueConstraint(
#TODO                fields=["project"],
#TODO                condition=Q(role="creator"),
#TODO                name="one_creator_per_project",
#TODO            ),
            models.UniqueConstraint(
                fields=["user", "project"],
                name="unique_user_project_binding",
            ),
        ]

        indexes = [
            models.Index(fields=["user", "is_hidden"]),
            models.Index(fields=["project", "role"]),
        ]


#FIXME    def __str__(self):
#FIXME       return "%s-%s" % (self.project.name, self.user.username)
#FIXME
#FIXME
#FIXME    @property
#FIXME    def groupname(self):
#FIXME        return f"p-{self.project.subpath}"
#FIXME
#FIXME    @property
#FIXME    def containers(self):
#FIXME        return { 
#FIXME            b.container
#FIXME            for b in self.project.containerbindings
#FIXME                .filter(project = self.project, container__user = self.user)
#FIXME                .select_related('container')
#FIXME                }


