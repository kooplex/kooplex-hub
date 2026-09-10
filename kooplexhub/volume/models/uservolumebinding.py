from django.db import models
from django.contrib.auth import get_user_model
from django.db.models import Q

User = get_user_model()

class UserVolumeBinding(models.Model):
    class Role(models.TextChoices):
        OWNER = (
            "owner",
            "The owner of this volume.",
        )
        ADMIN = (
            "administrator",
            "Can modify volume properties.",
        )
        COLLABORATOR = (
            "member",
            "User may access and mount this volume.",
        )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="volumebindings",
    )

    volume = models.ForeignKey(
        "volume.Volume",
        on_delete=models.CASCADE,
        related_name="userbindings",
    )

    role = models.CharField(
        max_length=16,
        choices=Role.choices,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "volume"],
                name="unique_user_volume_binding",
            ),
            models.UniqueConstraint(
                fields=["volume"],
                condition=models.Q(role="owner"),
                name="unique_volume_owner",
            ),
        ]

        indexes = [
            models.Index(fields=["user", "role"]),
            models.Index(fields=["volume", "role"]),
        ]

    def __str__(self):
        return f"{self.user} → {self.volume} ({self.role})"


