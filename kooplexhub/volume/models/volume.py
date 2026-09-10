from django.db import models
from django.db.models import Q
from django.core.validators import MinLengthValidator
from django.contrib.auth import get_user_model

from kooplexhub.lib import my_alphanumeric_validator


User = get_user_model()


class VolumeQuerySet(models.QuerySet):
    def present(self):
        return self.filter(provisioning_state=Volume.ProvisioningState.READY)

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
        from ..services.access import owned_volume_q
    
        if not user.is_authenticated:
            return self.none()
    
        return self.filter(
            owned_volume_q(user)
        ).distinct()

    def manageable_by(self, user):
        from ..services.access import manageable_volume_q

        if not user.is_authenticated:
            return self.none()

        return self.filter(
            manageable_volume_q(user)
        ).distinct()

    def visible_to(self, user):
        from ..services.access import visible_volume_q
    
        if not user.is_authenticated:
            return self.none()
    
        return self.filter(
            visible_volume_q(user)
        ).distinct()

    def attachable_by(self, user):
        from ..services.access import mountable_volume_q
    
        if not user.is_authenticated:
            return self.none()
    
        return (
            self.filter(
                mountable_volume_q(user),
                provisioning_state=Volume.ProvisioningState.READY,
            )
            .distinct()
        )

    def for_user(self, user):
        """
        Backwards-compatible alias.

        Prefer explicit methods in new code:
        visible_to(), attachable_by(), manageable_by(), owned_by().
        """
        return self.visible_to(user)



class Volume(models.Model):
    class ProvisioningState(models.TextChoices):
        PREPARING = "prp", "Preparing"
        READY = "rdy", "Ready"
        FAILED = "err", "Failed"
        DELETING = "del", "Deleting"

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

    provisioning_state = models.CharField(
        max_length=16,
        choices=ProvisioningState.choices,
        default=ProvisioningState.PREPARING,
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

    users = models.ManyToManyField(
        User,
        through="volume.UserVolumeBinding",
        related_name="volumes",
    )

    objects = VolumeQuerySet.as_manager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["claim", "subpath"],
                name="unique_volume_claim_subpath",
            ),
        ]

        indexes = [
            models.Index(fields=["scope", "provisioning_state"]),
            models.Index(fields=["claim", "folder"]),
        ]
        

    def __str__(self):
        return "Volume({}) /{} ({}:{})".format(self.scope, self.folder, self.claim, self.subpath)

    @property
    def is_present(self):
        return (
            self.provisioning_state 
            == self.ProvisioningState.READY
        )

    @property
    def is_preparing(self):
        return (
            self.provisioning_state
            == self.ProvisioningState.PREPARING
        )
    
    @property
    def is_deleting(self):
        return (
            self.provisioning_state
            == self.ProvisioningState.DELETING
        )

