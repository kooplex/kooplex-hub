import json, os
import re
from django.db import models

from kooplex.lib.gitlab import Gitlab
from kooplex.lib.libbase import get_settings

from .scope import ScopeType
from .image import Image

from .user import HubUser

class Project(models.Model):
    id = models.IntegerField(primary_key = True)
    name = models.TextField(max_length = 200, null = False)
    description = models.TextField(null=True)
    owner = models.ForeignKey(HubUser, null = True)
    image = models.ForeignKey(Image, null = True)
    scope = models.ForeignKey(ScopeType, null = True)

#    safename = models.TextField(max_length=200, null=True)
#    path = models.TextField(max_length=200, null=True)
#    path_with_namespace = models.TextField(max_length=200, null=True)
#    creator_id = models.IntegerField(null=True)
#    owner_name = models.CharField(max_length=200, null=True)
#    owner_username = models.CharField(max_length=200, null=True)
#    owner_id = models.IntegerField(null=True)
#    creator_name = models.CharField(max_length=200, null=True)
#    home = models.CharField(max_length=200, null=True)
#    shared_directory = models.CharField(max_length=200, null=True)
    # From docker api
####    gitwd = get_settings('volumes', 'git')
####
    def __str__(self):
        return "%s@%s" % (self.name, self.owner_username)

    def __lt__(self, p):
        return self.name < p.name

    class Meta:
        db_table = "kooplex_hub_project"

#####FIXME: get rid of init if possible
####    def init(self, gitlab_dict):
####        #try:
####        #    p = Project.objects.get(id=gitlab_dict['id'])
####        #if 1==2:
####        #   self = p
####        #else:
####
####        self.id=gitlab_dict['id']
####        self.name=gitlab_dict['name']
####        self.safename = self.get_safename()
####        self.path=gitlab_dict['path']
####        self.path_with_namespace=gitlab_dict['path_with_namespace']
####        self.owner_name=gitlab_dict['owner']['username']
####        self.owner_username=gitlab_dict['owner']['username']
####        self.owner_id=gitlab_dict['owner']['id']
####        self.creator_id=gitlab_dict['creator_id']
####
####        g = Gitlab()
####        creator = g.get_user_by_id(self.creator_id)
####        self.creator_name = creator['username']
####
####        self.description=gitlab_dict['description']
####        self.visibility=gitlab_dict['visibility']
####
#####FIXME: use home_ property instead
####        self.home = self.path_with_namespace.replace('/', '_')
####
#####FIXME: I guess this is not necessary
####    def get_safename(self):
####        return self.name.replace(" ",'-')
####
####    @property
####    def groupname_(self):
####        return re.split('([_a-z][-0-9_a-z]*)', self.name.lower())[1] if len(self.name) else "dummygroup"
####
####    @property
####    def image_(self):
####        return self.image.split('-')[-1]
####
####    @property
####    def safename_(self):
####        return os.path.join(self.path_with_namespace.replace('/', '_'))
####
####    @property
####    def gitdir_(self):
####        return os.path.join(self.gitwd, self.owner_username, self.path_with_namespace.replace('/', '_'))
####    def gitdir(self, username):
####        return os.path.join(self.gitwd, username, self.path_with_namespace.replace('/', '_'))
####
####    @property
####    def members_(self):
####        return UserProjectBinding.objects.get(project = self)
####
####    def get_binds(self):
####        return self.load_json(self.binds)
####
####    def set_binds(self, value):
####        self.binds = self.save_json(value)
####
####    def get_ports(self):
####        return self.load_json(self.ports)
####
####    def set_ports(self, value):
####        self.ports = self.save_json(value)
####
####    def get_volumes(self):
####        volumes = []
####        binds = self.get_binds()
####        if binds:
####            for key in binds:
####                volumes.append(binds[key]['bind'])
####        return volumes
####
####    def get_networking_config(self):
####        networking_config = None
####        if self.network:
####            networking_config = {
####                'EndpointsConfig': {
####                    self.network: {}
####                    }
####               }
####            if self.ip:
####                networking_config['EndpointsConfig'][self.network] = {
####                        'IPAMConfig': {
####                            'IPv4Address': self.ip,
####                            #'IPv6Address': '...',
####                        }
####                    }
####        return networking_config

class UserProjectBinding(models.Model):
    id = models.AutoField(primary_key = True)
    user = models.ForeignKey(HubUser, null = False)
    project = models.ForeignKey(Project, null = False)

#FIXME: el pldanyositas soran elvegezheto
#    def set(self, project, hub_user):
#       self.project = project
#       self.hub_user = hub_user

    def __str__(self):
       return "%s-%s" % (self.project.name, self.hub_user.username)
