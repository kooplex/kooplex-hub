from django.db import models

from . import Volume


class VolumeContainerBinding(models.Model):
    volume = models.ForeignKey(
        Volume, 
        on_delete=models.CASCADE, 
        related_name="containerbindings",
    )
    container = models.ForeignKey(
        "container.Container", 
        on_delete=models.CASCADE, 
        related_name="volumebindings",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["volume", "container"],
                name="unique_volume_container_binding",
            ),
        ]
