#FIXME: ooops equals to Image
import json
from django.db import models
from django.http import HttpResponseRedirect

from .modelbase import ModelBase
from kooplex.lib.smartdocker import Docker
from kooplex.hub.models.dashboard_server import Dashboard_server
from kooplex.lib.libbase import get_settings


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

    def Refresh_database(self, request='', *args, **kwargs):
        DockerImage.objects.all().delete()
        Dashboard_server.objects.all().delete()


        d = Docker()
        notebook_images = d.get_all_notebook_images()
        for image in notebook_images:
            i = DockerImage()
            i = i.from_docker_dict(image)
            i.save()
            dashboards_prefix = get_settings('dashboards', 'prefix', None, '')
            notebook_prefix = get_settings('prefix', 'name')
            dashboard_container_name = "%s-%s-"%(notebook_prefix, dashboards_prefix) + \
                                        i.name.split(notebook_prefix + "-notebook-")[1]
            docker_container = d.get_container(dashboard_container_name, original=True)
            # container, docker_container = d.get_container(dashboard_container_name)
            if docker_container:
                DS = Dashboard_server()
                DS.init(d, docker_container)
                DS.save()
        return HttpResponseRedirect("/admin")

#    def get_name(self):
#        return self.load_json(self.environment)

#    def set_name(self, value):
#        self.environment = self.save_json(value)
