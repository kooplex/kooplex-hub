from django.db import models
from django.urls import reverse
from django.db.models import Q
from django.core.validators import MinLengthValidator
from django.contrib.auth import get_user_model

from hub.models import Group


User = get_user_model()


class ProjectQuerySet(models.QuerySet):
    def member_of(
        self,
        user,
        *,
        include_hidden=False,
    ):
        """
        Projects where the user has an explicit
        Project membership binding, regardless
        of role.

        Includes:
        - CREATOR
        - ADMIN
        - COLLABORATOR
        """
        if not user or not user.is_authenticated:
            return self.none()

        qs = self.filter(
            userbindings__user=user,
        )

        if not include_hidden:
            qs = qs.filter(
                userbindings__is_hidden=False,
            )

        return qs.distinct()


    def created_by(self, user):
        from . import UserProjectBinding
        if not user.is_authenticated:
            return self.none()

        return self.filter(
            userbindings__user=user,
            userbindings__role=UserProjectBinding.Role.CREATOR,
        ).distinct()


    def for_dashboard(self, user):
        """
        Projects the user actively participates in.
    
        Includes projects created by the user and
        projects joined as another role.
        Does not include merely discoverable PUBLIC
        projects.
        """
        return self.member_of(
            user,
            include_hidden=False,
        )


    def joined_by(
        self,
        user,
        *,
        include_hidden=False,
    ):
        """
        Projects the user joined rather than created.
        """
        from . import UserProjectBinding
    
        qs = self.member_of(
            user,
            include_hidden=include_hidden,
        )
    
        return qs.exclude(
            userbindings__user=user,
            userbindings__role=(
                UserProjectBinding.Role.CREATOR
            ),
        ).distinct()



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


    def joinable_by(self, user):
        if not user or not user.is_authenticated:
            return self.none()
    
        member_ids = (
            self.member_of(
                user,
                include_hidden=True,
            )
            .values("pk")
        )
    
        return (
            self.filter(
                scope=Project.Scope.PUBLIC,
                state=Project.State.READY,
            )
            .exclude(
                pk__in=member_ids,
            )
            .distinct()
        )


    def attachable_by(self, user):
        """
        Projects the user may mount into an environment.
        Only fully provisioned projects are mountable.
        """
        return (
            self.member_of(
                user,
                include_hidden=False,
            )
            .filter(
                state=Project.State.READY
            )
        )        


    def manageable_by(self, user):
        """
        Projects where the user may modify project properties.
        """
        from . import UserProjectBinding
        if not user.is_authenticated:
            return self.none()

        return self.filter(
            userbindings__user=user,
            userbindings__role__in=[
                UserProjectBinding.Role.CREATOR,
                UserProjectBinding.Role.ADMIN,
            ],
        ).distinct()
        

class Project(models.Model):
    class Scope(models.TextChoices):
        PUBLIC = 'public', 'Any authenticated user can list and may join this project.'
        INTERNAL = 'internal', 'Only users in specific groups can list and may join this project.'
        PRIVATE = 'private', 'Only the creator can invite collaborators to this project.'

    class State(models.TextChoices):
        PREPARING = "prp", "Preparing"
        READY = "rdy", "Ready"
        PROVISION_FAILED = (
            "fld",
            "Provisioning failed",
        )
        DELETING = "del", "Deleting"
        DELETE_FAILED = (
            "dfl",
            "Deletion failed",
        )

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

    group = models.ForeignKey(
        Group,
        null=True,
        blank=True,
        default=None,
        on_delete=models.SET_NULL,
        related_name="projects",
        help_text=(
            "Filesystem/LDAP group controlling "
            "shared project access."
        ),
    )

    state = models.CharField(
        max_length=16,
        choices=State.choices,
        default=State.PREPARING,
    )

    last_operation_error = models.TextField(
        blank=True,
        default="",
    )

    last_operation_failed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    provisioned_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    deletion_requested_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    objects = ProjectQuerySet.as_manager()


