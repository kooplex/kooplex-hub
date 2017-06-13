import json, os
from django.db import models

from .modelbase import ModelBase
from .project import Project

from kooplex.lib.libbase import get_settings

class MountPoints(models.Model, ModelBase):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=200)
    type = models.CharField(max_length=200)
    host_mountpoint = models.CharField(max_length=200)
    container_mountpoint = models.CharField(max_length=200)
    project_id = models.IntegerField()
    #project = models.ForeignKey(Project, null=True, on_delete=models.CASCADE)

    def init(self, name, type, host_mountpoint, container_mountpoint, project):
        self.name = name
        self.type = type
        self.host_mountpoint = host_mountpoint
        self.container_mountpoint = container_mountpoint
        self.project_id = project.id
