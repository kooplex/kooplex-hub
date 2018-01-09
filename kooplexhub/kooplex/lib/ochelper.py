'''
@author: Jozsef Steger
@created: 05. 07. 2017
@summary: in favour of a user run a filesystem synchronization script in a separate container
'''

import docker

from kooplex.lib.libbase import get_settings
from kooplex.lib.smartdocker import Docker

class OCHelper:
    container_allusers = get_settings('impersonator', 'container_name')
    url_base = get_settings('owncloud', 'inner_url')

    def __init__(self, user, project):
        self.username = user.username
        self.folder = "_project." + project.safename_
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
        usercommand = [ "share.sh", "mkdir", self.folder ]
        self._execute(usercommand)

    def share(self, user):
        usercommand = [ "share.sh", "share", self.folder, user.username ]
        self._execute(usercommand)

    def unshare(self, user):
        usercommand = [ "share.sh", "unshare", self.folder, user.username ]
        self._execute(usercommand)

