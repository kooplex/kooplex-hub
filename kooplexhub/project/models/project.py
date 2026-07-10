import logging

from django.db import models
from django.db.models import Q
from django.core.validators import MinLengthValidator
from django.contrib.auth import get_user_model

User = get_user_model()

logger = logging.getLogger(__name__)


from django.db import models
from django.db.models import Q


class ProjectQuerySet(models.QuerySet):
    def joined_by(self, user, include_hidden=False):
        """
        Projects where the user has an explicit binding.
        Good for dashboards and mount picker.
        """
        if not user.is_authenticated:
            return self.none()

        qs = self.filter(userbindings__user=user)

        if not include_hidden:
            qs = qs.filter(userbindings__is_hidden=False)

        return qs.distinct()

    def visible_to(self, user):
        """
        Projects the user may see/list.

        Includes:
        - explicitly joined projects
        - public projects
        - maybe internal projects if group logic exists
        """
        if not user.is_authenticated:
            return self.none()

        qs = self.filter(
            Q(scope=Project.Scope.PUBLIC)
            | Q(userbindings__user=user)
        )

        # If INTERNAL scope is backed by groups, add it here.
        # Example, if Project has allowed_groups = ManyToManyField(Group):
        #
        # qs = qs | self.filter(
        #     scope=Project.Scope.INTERNAL,
        #     allowed_groups__in=user.groups.all(),
        # )

        return qs.distinct()

    def attachable_by(self, user):
        """
        Projects the user may mount into an environment.
        """
        return self.joined_by(user, include_hidden=False)

    def manageable_by(self, user):
        """
        Projects where the user may modify project properties.
        """
        if not user.is_authenticated:
            return self.none()

        return self.filter(
            userbindings__user=user,
            userbindings__role__in=[
                UserProjectBinding.Role.CREATOR,
                UserProjectBinding.Role.ADMIN,
            ],
        ).distinct()

    def created_by(self, user):
        if not user.is_authenticated:
            return self.none()

        return self.filter(
            userbindings__user=user,
            userbindings__role=UserProjectBinding.Role.CREATOR,
        ).distinct()
        

class Project(models.Model):
    class Scope(models.TextChoices):
        PUBLIC = 'public', 'Any authenticated user can list and may join this project.'
        INTERNAL = 'internal', 'Only users in specific groups can list and may join this project.'
        PRIVATE = 'private', 'Only the creator can invite collaborators to this project.'

    name = models.CharField(
        max_length=200,
        validators=[
            MinLengthValidator(3, message="Name must be at least 3 characters.")
        ],
    )

    description = models.TextField(
        blank=True,
        null=True,
        validators=[
            MinLengthValidator(5, message="Description must be at least 5 characters.")
        ],
    )

    scope = models.CharField(
        max_length=16,
        choices=Scope.choices,
        default=Scope.PRIVATE,
    )

    subpath = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        unique=True,
    )

    preferred_image = models.ForeignKey(
        "container.Image",
        on_delete=models.SET_NULL,
        default=None,
        null=True,
        blank=True,
    )

    members = models.ManyToManyField(
        User,
        through="project.UserProjectBinding",
        related_name="projects",
    )

    objects = ProjectQuerySet.as_manager()


    def __str__(self):
        return self.name 

    def __lt__(self, p):
        return self.name < p.name


    @property
    def groupname(self):
        return self.userbindings.first().groupname

    @property
    def group(self):
        from hub.models import Group
        return Group.objects.filter(name=self.groupname, grouptype=Group.TP_PROJECT).first()

    @property
    def volumes(self):
        return {
            b.volume
            for b in self.volumebindings
                     .select_related('volume')
        } if self.pk else {}


    # factory functions
    @classmethod
    def get_userproject(cls, pk, user):
        return cls.objects.filter(pk=pk).filter(userbindings__user=user).first()
