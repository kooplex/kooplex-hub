import logging

from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

logger = logging.getLogger(__name__)

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
            "User can mount this volume read-only.",
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
        ]

        indexes = [
            models.Index(fields=["user", "role"]),
            models.Index(fields=["volume", "role"]),
        ]

    def __str__(self):
        return f"{self.user} → {self.volume} ({self.role})"




    def volumecontainerbindings(self):
        from ..models import VolumeContainerBinding
        return VolumeContainerBinding.objects.filter(volume = self.volume, container__user = self.user)


