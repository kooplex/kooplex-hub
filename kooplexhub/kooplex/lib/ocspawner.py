import sys, os
import getopt
import json
import string
import uuid
import random
import docker
import requests as req
from os import path
from netaddr import IPAddress
from time import sleep
from io import BytesIO
from distutils.dir_util import mkpath

from kooplex.lib.libbase import LibBase, get_settings
from kooplex.lib.restclient import RestClient
from kooplex.lib.smartdocker import Docker
from kooplex.lib.proxy import Proxy
from kooplex.lib.jupyter import Jupyter
from kooplex.hub.models import Container, Notebook, Session, Project, MountPointProjectBinding, HubUser

from kooplex.lib import ldap

from kooplex.lib.debug import *

class OCSpawner(RestClient):
    image = 'kooplex-occ'
    sync_folder = '/syncme'
   
    def __init__(self, user):
        self.user = user
        d = Docker()
        url = d.get_docker_url()
        self.dockerclient = docker.client.Client(base_url = url)

    @property
    def username_(self):
        return self.user.username

    @property
    def container_name_(self):
        return "%s-%s" % (self.image, self.username_)

    @property
    def binds_(self):
        srv_path = get_settings('users', 'srv_dir', None, '')
        binds = {}
        home_host = os.path.join(srv_path, 'home', self.username_)
        home_container = os.path.join('/home', self.username_)
        oc_host = os.path.join(srv_path, '_oc', self.username_)
        oc_container = self.sync_folder
        binds[home_host] = {'bind': home_container, 'mode': 'ro'}
        binds[oc_host] = {'bind': oc_container, 'mode': 'rw'}
        return binds

    @property
    def volumes_(self):
        return [ x['bind'] for x in self.binds_.values() ]

    @property
    def env_(self):
        return {
            'FOLDER_SYNC': self.sync_folder,
            'URL_OWNCLOUD': 'http://kooplex-nginx/owncloud/', 
            'S_UID': self.user.uid, 
            'S_GID': self.user.gid,
            'S_UNAME': self.username_
        }

    @property
    def state_(self):
        for ctr in filter(lambda x: x['Image'] == self.image, self.dockerclient.containers()):
            if '/' + self.container_name_ in ctr['Names']:
                return ctr['State']
        return 'missing'

#FIXME: url, network hardcoded
    def start(self):
        assert self.state_ == 'missing', "Cannot start %s, because its state is %s" % (self.container_name_, self.state_)
        response = self.dockerclient.create_container(
            image = self.image,
            environment = self.env_,
            volumes = self.volumes_,
            host_config = self.dockerclient.create_host_config(binds = self.binds_),
            name = self.container_name_,
            detach = True,
            networking_config =  { 'EndpointsConfig': { 'kooplex-net': {} } },
            command = '/start.sh',
        )
        return self.dockerclient.start( container = response['Id'] )

    def stop(self):
        assert self.state_ == 'running', "Cannot stop %s, because its state is %s" % (self.container_name_, self.state_)
        self.dockerclient.remove_container(container = self.container_name_, force = True)

