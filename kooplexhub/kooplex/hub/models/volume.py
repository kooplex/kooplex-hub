import os

from django.db import models

from .project import Project
from .user import User
from kooplex.lib import get_settings

class Volume(models.Model):
    id = models.AutoField(primary_key = True)
    name = models.CharField(max_length = 64, unique = True)
    displayname = models.CharField(max_length = 64)
    description = models.TextField(null = True)

    def __str__(self):
        return self.displayname

    def mode(self, user):
        if hasattr(self, 'owner'):
            if self.owner == user:
                return "rw"
        try:
            upvb = UserPrivilegeVolumeBinding.objects.get(volume = self, user = user)
            return "rw" if upvb.readwrite else "ro"
        except UserPrivilegeVolumeBinding.DoesNotExist:
            return "ro"

class FunctionalVolume(Volume):
    owner = models.ForeignKey(User, null = True)

    @property
    def volumename(self):
        return get_settings('volumes', 'pattern_functionalvolumename') % { 'name': self.name }
 
    @property
    def mountpoint(self):
        return get_settings('spawner', 'pattern_mnt_functionalvolume') % { 'name': self.name }
 
class StorageVolume(Volume):
    groupid = models.IntegerField(null = True)

    @property
    def volumename(self):
        return get_settings('volumes', 'pattern_storagevolumename') % { 'name': self.name }
 
    @property
    def mountpoint(self):
        return get_settings('spawner', 'pattern_mnt_storagevolume') % { 'name': self.name }
 

class UserPrivilegeVolumeBinding(models.Model):
    id = models.AutoField(primary_key = True)
    volume = models.ForeignKey(Volume, null = True)
    user = models.ForeignKey(User, null = True)
    readwrite = models.BooleanField(default = False)

    def __str__(self):
        return "%s@%s" % (self.user, self.volume)

class VolumeProjectBinding(models.Model):
    id = models.AutoField(primary_key = True)
    volume = models.ForeignKey(Volume, null = False)
    project = models.ForeignKey(Project, null = False)
    #readwrite = models.BooleanField(default = False)

    def __str__(self):
       return "%s-%s" % (self.project.name, self.volume.name)



#    @property
#    def container_mountpoint_(self):
#        return os.path.join('/vol', self.name)

#    def create(self, uid = 0, gid = 0):
#        d = Docker()
#        url = d.get_docker_url()
#        dockerclient = docker.client.Client(base_url = url)
#        resp = dockerclient.create_volume(name = self.name)
#        os.chown(resp['Mountpoint'], uid, gid)
#        # a typical response looks like
#        # {'Mountpoint': '/var/lib/docker/volumes/kortefa/_data', 'Name': 'kortefa', 'Labels': None, 'Scope': 'local', 'Options': {}, 'Driver': 'local'}
#        # maybe this info should be part of the model and be saved now
#        self.save()
#        return resp
#
#    def delete(self):
#        pass



def init_model():
    from kooplex.lib import Docker
    # the list of the functional and storage volume names based on API information
    #FIXME: decide what to do with volumes present in the model but not present in the system
    for volume in Docker().list_volumenames():
        vname = volume['name']
        if volume['volumetype'] == 'functional':
            try:
                FunctionalVolume.objects.get(name = vname)
            except FunctionalVolume.DoesNotExist:
                description = "Functional volume %s automatically detected and added. Ask an administrator to provide a nice displayname and set the owner" % vname
                FunctionalVolume(name = vname, displayname = vname, description = description).save()
        elif volume['volumetype'] == 'storage':
            try:
                StorageVolume.objects.get(name = vname)
            except StorageVolume.DoesNotExist:
                description = "Storage volume %s automatically detected and added. Ask an administrator to provide a nice displayname and set the group id" % vname
                StorageVolume(name = vname, displayname = vname, description = description).save()

