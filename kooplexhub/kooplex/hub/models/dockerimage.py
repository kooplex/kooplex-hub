import json
from django.db import models

from .modelbase import ModelBase

class DockerImage(models.Model, ModelBase):
    #id = models.UUIDField(primary_key=True)
    id = models.CharField(primary_key=True,max_length=200)
    name = models.CharField(max_length=200)

    class Meta:
        db_table = "kooplex_hub_dockerimage"

    def from_docker_dict(docker, docker_dict):
        I = DockerImage()
        I.id=docker_dict['Id']
        I.name=docker_dict['RepoTags'][0].split(":")[0]
        return I

#    def get_name(self):
#        return self.load_json(self.environment)

#    def set_name(self, value):
#        self.environment = self.save_json(value)
