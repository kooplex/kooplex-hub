from django.db import models
from django.db.models import Q
from django.core.validators import MinLengthValidator
from django.contrib.auth import get_user_model

from kooplexhub.lib import my_alphanumeric_validator


User = get_user_model()


class VolumeQuerySet(models.QuerySet):
    def present(self):
        return self.filter(is_present=True)

    def bound_to(self, user):
        """
        Volumes where the user has an explicit UserVolumeBinding.
        """
        if not user.is_authenticated:
            return self.none()

        if user.is_superuser:
            return self

        return self.filter(
            userbindings__user=user,
        ).distinct()

    def owned_by(self, user):
        if not user.is_authenticated:
            return self.none()

        if user.is_superuser:
            return self

        return self.filter(
            userbindings__user=user,
            userbindings__role=UserVolumeBinding.Role.OWNER,
        ).distinct()

    def manageable_by(self, user):
        """
        Volumes where the user may modify properties.
        """
        if not user.is_authenticated:
            return self.none()

        if user.is_superuser:
            return self

        return self.filter(
            userbindings__user=user,
            userbindings__role__in=[
                UserVolumeBinding.Role.OWNER,
                UserVolumeBinding.Role.ADMIN,
            ],
        ).distinct()

    def visible_to(self, user):
        """
        Volumes the user may list/see.
        """
        if not user.is_authenticated:
            return self.none()

        if user.is_superuser:
            return self

        group_ids = user.groups.values_list("id", flat=True)

        return self.filter(
            Q(scope=Volume.Scope.PUBLIC)
            | Q(scope=Volume.Scope.ATTACHMENT)
            | Q(userbindings__user=user)
#            | Q(
#                scope=Volume.Scope.INTERNAL,
#                allowed_groups__id__in=group_ids,
#            )
        ).distinct()

    def attachable_by(self, user):
        """
        Volumes the user may mount into an environment.

        For now, same as visible_to(), but keeping it separate is useful.
        Later you may decide that visible != mountable.
        """
        return self.visible_to(user).present()

    def for_user(self, user):
        """
        Backwards-compatible alias.

        Prefer explicit methods in new code:
        visible_to(), attachable_by(), manageable_by(), owned_by().
        """
        return self.visible_to(user)



class Volume(models.Model):
    class Scope(models.TextChoices):
        PRIVATE = (
            "private",
            "Owner can invite collaborators to use this volume.",
        )
        INTERNAL = (
            "internal",
            "Users in specific groups can list and may mount this volume.",
        )
        PUBLIC = (
            "public",
            "Authenticated users can list and may mount this volume.",
        )
        ATTACHMENT = (
            "attachment",
            "Users can create, list and may mount attachments.",
        )

    folder = models.CharField(
        max_length=64,
        validators=[
            my_alphanumeric_validator(
                "Enter a clean volume name containing only letters and numbers."
            )
        ],
    )

    description = models.TextField(
        blank=False,
        validators=[
            MinLengthValidator(
                5,
                message="Description must be at least 5 characters.",
            )
        ],
    )

    allow_shared_write = models.BooleanField(
        default=False,
        help_text=(
            "Allow non-owner users who have access to this volume "
            "to mount it read-write."
        ),
    )    

    claim = models.CharField(
        max_length=64,
        blank=False,
    )

    subpath = models.CharField(
        max_length=64,
        blank=True,
    )

    scope = models.CharField(
        max_length=16,
        choices=Scope.choices,
        default=Scope.ATTACHMENT,
    )

    is_present = models.BooleanField(default=True)

    users = models.ManyToManyField(
        User,
        through="volume.UserVolumeBinding",
        related_name="volumes",
    )

    objects = VolumeQuerySet.as_manager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["claim", "folder"],
                name="unique_volume_claim_folder",
            ),
        ]

        indexes = [
            models.Index(fields=["scope", "is_present"]),
            models.Index(fields=["claim", "folder"]),
        ]
        

    def __str__(self):
        return "Volume({}) /{} ({}:{})".format(self.scope, self.folder, self.claim, self.subpath)

