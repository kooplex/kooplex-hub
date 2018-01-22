import os
from django.db import models
from django.utils import timezone

from kooplex.lib import get_settings
from kooplex.lib.filesystem import G_OFFSET

from .user import User
from .project import Project
from .volume import Volume, VolumeProjectBinding
from .image import Image

class ContainerType(models.Model):
    id = models.AutoField(primary_key = True)
    name = models.CharField(max_length = 32)

class Container(models.Model):
    id = models.AutoField(primary_key = True)
    name = models.CharField(max_length = 200, null = True)
    user = models.ForeignKey(User, null = True)
    project = models.ForeignKey(Project, null = True)

    image = models.ForeignKey(Image, null = True)

    container_type = models.ForeignKey(ContainerType, null = False)

    launched_at = models.DateTimeField(default = timezone.now)
    is_running = models.BooleanField(default = False)

    def __lt__(self, c):
        return self.launched_at < c.launched_at

    def init(self):
        self.image = self.project.image
        for vpb in VolumeProjectBinding.objects.filter(project = self.project):
            vcb = VolumeContainerBinding(container = self, volume = vpb.volume)
            vcb.save()

    @property
    def volumes(self):
        for vcb in VolumeContainerBinding.objects.filter(container = self):
            yield vcb.volume

    @property
    def proxy_path(self):
        info = { 'containername': self.name }
        return get_settings('spawner', 'pattern_proxypath') % info

    @property
    def url(self):
        return "http://%s:%d" % (self.name, 8000) #FIXME: PORT hardcoded

    @property
    def url_with_token(self):
        return os.path.join(get_settings('hub', 'base_url'), self.proxy_path, '?token=%s' % self.user.token)

    @property
    def environment(self):
        if self.container_type.name == 'notebook':
            return {
                'NB_USER': self.user.username,
                'NB_UID': self.user.uid,
                'NB_GID': self.user.gid,
                'NB_URL': self.proxy_path,
                'NB_PORT': 8000,
                'NB_TOKEN': self.user.token,
                'PR_ID': self.project.id,
                'PR_NAME': self.project.name,
                'PR_FULLNAME': self.project.name,
                'PR_PWN': self.project.name_with_owner,
                'PR_MEMBERS': ",".join([ str(u.uid) for u in self.project.collaborators ]),
                'PR_URL': self.project.url_gitlab,
                'GID_OFFSET': G_OFFSET,
        #        'MNT_GIDS': ",".join(mpgids)  #FIXME: still missing
            }
        else:
            raise NotImplementedError

class VolumeContainerBinding(models.Model):
    id = models.AutoField(primary_key = True)
    volume = models.ForeignKey(Volume, null = False)
    container = models.ForeignKey(Container, null = False)

    def __str__(self):
       return "%s-%s" % (self.container.name, self.volume.name)


def init_model():
    containertypes = [ 'notebook', 'dashboard' ]
    for ct in containertypes:
        try:
            ContainerType.objects.get(name = ct)
        except ContainerType.DoesNotExist:
            ContainerType(name = ct).save()

