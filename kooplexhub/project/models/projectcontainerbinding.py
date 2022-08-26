import os
import logging

from django.db import models

from container.models import Container
from project.models import Project

logger = logging.getLogger(__name__)

class ProjectContainerBinding(models.Model):
    project = models.ForeignKey(Project, on_delete = models.CASCADE, null = False)
    container = models.ForeignKey(Container, on_delete = models.CASCADE, null = False)

    def __str__(self):
        return f"<ProjectContainerBinding {self.project}-{self.container}>"

