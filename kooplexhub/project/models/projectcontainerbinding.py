from django.db import models


class ProjectContainerBinding(models.Model):
    project = models.ForeignKey(
        "project.Project", 
        on_delete=models.CASCADE, 
        related_name="containerbindings",
    )
    container = models.ForeignKey(
        "container.Container", 
        on_delete=models.CASCADE, 
        related_name="projectbindings",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["project", "container"],
                name="unique_project_container_binding",
            ),
        ]

    def __str__(self):
        return f"<ProjectContainerBinding {self.project}-{self.container}>"

