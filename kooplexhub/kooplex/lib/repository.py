import docker
import os
#FIXME: get rid of smartdocker
from kooplex.lib.smartdocker import Docker

class repository:
    container_git = 'kooplex-git'

    def __init__(self, user, project):
        self.user = user.username
        self.repo = project.path_with_namespace
        self.gitdir = project.home_
        d = Docker()
        url = d.get_docker_url()
        self.dockerclient = docker.client.Client(base_url = url)
        self.sshagentsock = os.path.join('/tmp', self.user)
        try:
            self.__execute('ssh-agent -a %s' % self.sshagentsock)
            self.__execute('SSH_AUTH_SOCK=%s ssh-add \$HOME/.ssh/gitlab.key' % self.sshagentsock)
        except:
            # ssh-agent already running
            pass

    def __execute(self, command):
        usercommand = [ "sudo", "-i", "-u", self.user, "sh", "-c", "cd %s ; SSH_AUTH_SOCK=%s %s" % (self.gitdir, self.sshagentsock, command) ]
        x = self.dockerclient.exec_create(container = self.container_git, cmd = usercommand)
        response = self.dockerclient.exec_start(exec_id = x['Id'], stream = False)
        check = self.dockerclient.exec_inspect(exec_id = x['Id'])
        assert check['ExitCode'] == 0, check
        return response

    def status(self):
        pass

    def add(self, files):
        command = "git add %s" % " ".join(files)
        resp = self.__execute(command)
        assert len(resp) == 0, "git add -> %s" % resp

    def remove(self, files):
        command = "git rm %s" % " ".join(files)
        resp = self.__execute(command)
        assert len(resp) == 0, "git add -> %s" % resp

    def commit(self, message):
        command = "git commit -m '%s'" % (message)
        return self.__execute(command)

    def push(self):
        command = "git push"
        return self.__execute(command)
