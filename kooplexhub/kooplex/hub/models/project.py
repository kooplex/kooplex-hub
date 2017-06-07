import json, os
from django.db import models

from .modelbase import ModelBase
from .session import Session

from kooplex.lib.gitlab import Gitlab
from kooplex.lib.libbase import get_settings

class Project(models.Model, ModelBase):
    # From gitlab api projects
    id = models.IntegerField(primary_key=True)
    name = models.TextField(max_length=200, null=True)
    path = models.TextField(max_length=200, null=True)
    path_with_namespace = models.TextField(max_length=200, null=True)
    home = models.CharField(max_length=200, null=True)
    owner_name = models.CharField(max_length=200, null=True)
    owner_username = models.CharField(max_length=200, null=True)
    owner_id = models.IntegerField(null=True)
    creator_id = models.IntegerField(null=True)
    creator_name = models.CharField(max_length=200, null=True)
    description = models.TextField(null=True)
    visibility = models.TextField(null=True)

    # From gitlab api projectmembers
    gids = models.CharField(max_length=300,null=True)

    # From docker api
    image = models.CharField(max_length=200)
    environment = models.TextField(null=True)
    binds = models.TextField(null=True)



    class Meta:
        db_table = "kooplex_hub_project"

    def init(self, gitlab_dict):
        p = Project.objects.get(id=gitlab_dict['id'])
        if 1==2:
           self = p
        else:

            self.id=gitlab_dict['id']
            self.name=gitlab_dict['name']
            self.path=gitlab_dict['path']
            self.path_with_namespace=gitlab_dict['path_with_namespace']
            self.owner_name=gitlab_dict['owner']['username']
            self.owner_username=gitlab_dict['owner']['username']
            self.owner_id=gitlab_dict['owner']['id']
            self.creator_id=gitlab_dict['creator_id']

            g = Gitlab()
            creator = g.get_user_by_id(self.creator_id)
            self.creator_name = creator['username']

            self.description=gitlab_dict['description']
            self.visibility=gitlab_dict['visibility']

            srv_dir = get_settings('users', 'srv_dir')
            home_dir = get_settings('users', 'home_dir')
            home_dir = home_dir.replace('${username}', self.creator_name)
            project_dir = get_settings('users', 'project_dir')
            project_dir = project_dir.replace('${path_with_namespace}', p.path_with_namespace)
            self.home = os.path.join(srv_dir, home_dir, project_dir)

    def from_gitlab_dict_projectmembers(self, list_of_members):
        self.gids = ""
        for E in list_of_members:
            self.gids +="%d,"%E['id']

    def get_member(self):
        return self.load_json(self.environment)

    def set_member(self, value):
        self.environment = self.save_json(value)

    def get_binds(self):
        return self.load_json(self.binds)

    def set_binds(self, value):
        self.binds = self.save_json(value)

    def get_ports(self):
        return self.load_json(self.ports)

    def set_ports(self, value):
        self.ports = self.save_json(value)

    def get_volumes(self):
        volumes = []
        binds = self.get_binds()
        if binds:
            for key in binds:
                volumes.append(binds[key]['bind'])
        return volumes

    def get_networking_config(self):
        networking_config = None
        if self.network:
            networking_config = {
                'EndpointsConfig': {
                    self.network: {}
                    }
               }
            if self.ip:
                networking_config['EndpointsConfig'][self.network] = {
                        'IPAMConfig': {
                            'IPv4Address': self.ip,
                            #'IPv6Address': '...',
                        }
                    }
        return networking_config