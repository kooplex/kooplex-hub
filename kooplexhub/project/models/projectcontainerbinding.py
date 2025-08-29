import os
import logging

from django.db import models


logger = logging.getLogger(__name__)

class ProjectContainerBinding(models.Model):
    project = models.ForeignKey('project.Project', on_delete = models.CASCADE, related_name = 'containerbindings')
    container = models.ForeignKey('container.Container', on_delete = models.CASCADE, related_name = 'projectbindings')

    def __str__(self):
        return f"<ProjectContainerBinding {self.project}-{self.container}>"

