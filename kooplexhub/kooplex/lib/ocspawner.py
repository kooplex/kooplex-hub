'''
@author: Jozsef Steger
@created: 05. 07. 2017
@summary: in favour of a user run a filesystem synchronization script in a separate container
'''

import os
import docker

from kooplex.lib.libbase import get_settings
from kooplex.lib.restclient import RestClient
from kooplex.lib.smartdocker import Docker

class OCSpawner:
    image = 'kooplex-occ'
    url_owncloud = 'http://kooplex-nginx/ownCloud/' #FIXME: still hardcoded
    network = get_settings('docker', 'network', None, 'kooplex-net')
    sync_folder = '/syncme'
    srv_path = get_settings('users', 'srv_dir', None, '')

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
        binds = {}
        home_host = os.path.join(self.srv_path, 'home', self.username_)
        home_container = os.path.join('/home', self.username_)
        oc_host = os.path.join(self.srv_path, '_oc', self.username_)
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
            'URL_OWNCLOUD': self.url_owncloud,
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

    def start(self):
        assert self.state_ == 'missing', "Cannot start %s, because its state is %s" % (self.container_name_, self.state_)
        response = self.dockerclient.create_container(
            image = self.image,
            environment = self.env_,
            volumes = self.volumes_,
            host_config = self.dockerclient.create_host_config(binds = self.binds_),
            name = self.container_name_,
            detach = True,
            networking_config =  { 'EndpointsConfig': { self.network: {} } },
            command = '/start.sh',
        )
        return self.dockerclient.start( container = response['Id'] )

    def stop(self):
        assert self.state_ == 'running', "Cannot stop %s, because its state is %s" % (self.container_name_, self.state_)
        self.dockerclient.remove_container(container = self.container_name_, force = True)

class OCHelper:
    container_allusers = 'kooplex-git'  #FIXME: hardcoded. to be renamed, also used by repository
    ocmountpoint = '/oc'
    url_base = "http://kooplex-nginx/ownCloud"  # FIXME: IPAddress hardcoded

    def __init__(self, user, project):
        self.username = user.username
        self.subfolder = "_project." + project.safename_
        self.folder = os.path.join(self.ocmountpoint, self.username, self.subfolder)
        d = Docker()
        url = d.get_docker_url()
        self.dockerclient = docker.client.Client(base_url = url)

    def _execute(self, usercommand):
        command = [ "sudo", "-i", "-u", self.username, "sh", "-c", " ".join(usercommand) ]
        x = self.dockerclient.exec_create(container = self.container_allusers, cmd = command)
        self.dockerclient.exec_start(exec_id = x['Id'], stream = False)
        check = self.dockerclient.exec_inspect(exec_id = x['Id'])
        assert check['ExitCode'] == 0, check

    def mkdir(self):
        usercommand = [ "mkdir", "-p %s" % self.folder ]
        self._execute(usercommand)
        self.synch()

    def synch(self):
        usercommand = [ "owncloudcmd", "-n %s" % self.folder, self.url_base ]
        self._execute(usercommand)

    def share(self, user):
        self.mkdir()
        usercommand = [ "share.sh", "share", self.subfolder, user.username ]
        self._execute(usercommand)

    def unshare(self, user):
        usercommand = [ "share.sh", "unshare", self.subfolder, user.username ]
        self._execute(usercommand)
