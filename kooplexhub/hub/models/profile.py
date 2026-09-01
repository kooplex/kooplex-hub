from django.db import models
from django.contrib.auth.models import User


class Profile(models.Model):
    class State(models.TextChoices):
        PREPARING = "prp", "Preparing"
        READY = "rdy", "Ready"
        PROVISION_FAILED = (
            "pfl",
            "Provisioning failed",
        )
        DELETING = "del", "Deleting"
        DELETE_FAILED = (
            "dfl",
            "Deletion failed",
        )
    
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE,
        related_name="profile",
    )

    state = models.CharField(
        max_length=3,
        choices=State.choices,
        default=State.PREPARING,
    )

    uid_number = models.PositiveIntegerField(
        null=True,
        blank=True,
        unique=True,
    )

    gid_number = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    token = models.CharField(
        max_length=64, 
        null=True,
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

    can_createproject = models.BooleanField(default = True)
    can_createimage = models.BooleanField(default = False)
    can_createattachment = models.BooleanField(default = False)
    can_createcourse = models.BooleanField(default = False)
    can_runjob = models.BooleanField(default = False)
    can_choosenode = models.BooleanField(default = False)
    can_teleport = models.BooleanField(default = False)
    has_scratch = models.BooleanField(default = False)

