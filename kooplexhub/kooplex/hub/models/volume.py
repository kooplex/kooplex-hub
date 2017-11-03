import docker.client
from django.db import models
import os

#TODO: fall back to native module
from kooplex.lib.smartdocker import Docker
from .project import Project



class Volume(models.Model):
    id = models.AutoField(primary_key = True)
    name = models.CharField(max_length = 64, unique = True)
    displayname = models.CharField(max_length = 64)
    description = models.TextField(null = True)

    def __str__(self):
        return self.name

    def create(self, uid = 0, gid = 0):
        d = Docker()
        url = d.get_docker_url()
        dockerclient = docker.client.Client(base_url = url)
        resp = dockerclient.create_volume(name = self.name)
        os.chown(resp['Mountpoint'], uid, gid)
        # a typical response looks like
        # {'Mountpoint': '/var/lib/docker/volumes/kortefa/_data', 'Name': 'kortefa', 'Labels': None, 'Scope': 'local', 'Options': {}, 'Driver': 'local'}
        # maybe this info should be part of the model and be saved now
        self.save()
        return resp

    def delete(self):
        pass

    @property
    def container_mountpoint_(self):
        return os.path.join('/vol', self.name)


class VolumeProjectBinding(models.Model):
    id = models.AutoField(primary_key = True)
    volume = models.ForeignKey(Volume, null = False)
    project = models.ForeignKey(Project, null = False)

    def __str__(self):
       return "%s-%s" % (self.project.name, self.volume.name)

    @property
    def accessrights_(self):
        return 'rw'
