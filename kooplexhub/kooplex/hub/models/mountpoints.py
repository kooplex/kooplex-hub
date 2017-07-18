import json, os
from django.db import models

from .modelbase import ModelBase
from .project import Project
from .project import HubUser

from kooplex.lib.libbase import get_settings

class MountPoints(models.Model, ModelBase):
    id = models.AutoField(primary_key = True)
    name = models.CharField(max_length = 200)
    type = models.CharField(max_length = 200)
    host_mountpoint = models.CharField(max_length = 200)
    host_groupid = models.IntegerField(null = True)

    def __str__(self):
        return self.name

    def init(self, name, type, host_mountpoint, container_mountpoint, project):
        self.name = name
        self.type = type
        self.host_mountpoint = host_mountpoint
    
    @property
    def server_(self):
        if self.type == 'nfs':
            return self.host_mountpoint.split(':')[0]
        else:
            raise Exception('Unknonwn type %s' %  self.type)

    @property
    def mountpoint_(self):
        if self.type == 'local':
            return self.host_mountpoint.split(':')[0]
        elif self.type == 'nfs':
            return self.host_mountpoint.split(':')[1]
        else:
            raise Exception('Unknonwn type %s' %  self.type)

    @property
    def accessrights_(self):
        if self.type == 'local':
            return self.host_mountpoint.split(':')[1] if self.host_mountpoint.count(':') == 1 else 'ro'
        if self.type == 'nfs':
            return self.host_mountpoint.split(':')[2] if self.host_mountpoint.count(':') == 2 else 'ro'
        else:
            raise Exception('Unknonwn type %s' %  self.type)

class MountPointProjectBinding(models.Model, ModelBase):
    id = models.AutoField(primary_key = True)
    mountpoint = models.ForeignKey(MountPoints, null = True)
    project = models.ForeignKey(Project, null = True)
    readwrite = models.BooleanField(default = False)

    def __str__(self):
        return "%s:%s" % (self.project, self.mountpoint)
    
class MountPointPrivilegeBinding(models.Model, ModelBase):
    id = models.AutoField(primary_key = True)
    mountpoint = models.ForeignKey(MountPoints, null = True)
    user = models.ForeignKey(HubUser, null = True)
    accessrights = models.CharField(max_length = 16)

    def __str__(self):
        return "%s@%s" % (self.user, self.mountpoint)

    @property
    def rw_(self):
        if self.accessrights == 'ro':
            return False
        if self.mountpoint.accessrights_ == 'ro':
            return False
        return True

