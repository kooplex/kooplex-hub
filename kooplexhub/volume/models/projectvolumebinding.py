from django.db import models

from . import Volume

class ProjectVolumeBinding(models.Model):
    project = models.ForeignKey(
        "project.Project", 
        on_delete=models.CASCADE, 
        related_name="volumebindings",
    )
    volume = models.ForeignKey(
        Volume, 
        on_delete=models.CASCADE, 
        related_name="projectbindings",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["project", "volume"],
                name="unique_project_volume_binding",
            ),
        ]

    def __str__(self):
       return "%s-%s" % (self.project.name, self.volume.folder)

