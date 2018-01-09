import json
from django.db import models
from django.utils import timezone

from .user import HubUser
from .project import Project
from .volume import Volume, VolumeProjectBinding
from .image import Image

class Container(models.Model):
    id = models.UUIDField(primary_key = True)  #FIXME: TO BE REPLACED BY IntegerField
    name = models.CharField(max_length = 200, null = True)
    user = models.ForeignKey(HubUser, null = True)
    project = models.ForeignKey(Project, null = True)

    image = models.ForeignKey(Image, null = True)
    ip = models.GenericIPAddressField()
    environment = models.TextField(null = True)
    command = models.TextField(null = True)

    container_type = models.ForeignKey(ContainerType, null = False)

    proxy_path = models.CharField(max_length = 200)

    launched_at = models.DateTimeField(default = timezone.now)
    state = models.CharField(max_length = 15, null = True)

#FIXME: these two are to be removed
    binds = models.TextField(null = True)
    project_owner = models.CharField(max_length=200, null=True)
    project_name = models.CharField(max_length=200, null=True)
###################################################################

    def __lt__(self, c):
        return self.launched_at < c.launched_at

    class Meta:
        db_table = "kooplex_hub_container"

    def save(self):
        self.image = self.project.image
        models.Model.save(self)
        for vpb in VolumeProjectBinding.objects.filter(project = self.project):
            vcb = VolumeContainerBinding(container = self, volume = vpb.volume)
            vcb.save()

##    def from_docker_dict(docker, dict):
##        c = Container()
##        c.id=dict['Id']
##        c.name=dict['Names'][0][1:]
##        c.image=dict['Image']
##        try:
##            c.network = list(dict['NetworkSettings']['Networks'].keys())[0]
##            c.ip = dict['NetworkSettings']['Networks'][c.network]['IPAMConfig']['IPv4Address']
##        except:
##            pass
##        c.command = dict['Command']
##        c.environment = None    # not returned by api
##        c.volumes = None        # TODO
##        c.ports = dict['Ports']          # TODO
##        c.state = dict['State']    # created|restarting|running|paused|exited|dead
##        return c

class ContainerType(models.Model):
    id = models.AutoField(primary_key = True)
    name = models.CharField(max_length = 32)

class VolumeContainerBinding(models.Model):
    id = models.AutoField(primary_key = True)
    volume = models.ForeignKey(Volume, null = False)
    container = models.ForeignKey(Container, null = False)

    def __str__(self):
       return "%s-%s" % (self.container.name, self.volume.name)


def init_model():
    containertypes = [ 'notebook', 'dashboard' ]
    for ct in containertypes:
        cti = ContainerType.objects.get(name = ct)
        if cti is None:
            cti = ContainerType(name = ct)
            cti.save()

