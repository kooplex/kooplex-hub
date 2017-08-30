'''
@author: Jozsef Steger
@created: 25. 07. 2017
@summary: issue git commands in favor of a user inside a docker contaner
'''

import docker
import os
import re
#FIXME: get rid of smartdocker
from kooplex.lib.smartdocker import Docker

class repository:
    container_git = 'kooplex-git'

    def __init__(self, user, project):
        self.user = user.username
        self.repo = project.path_with_namespace
        #FIXME:
        ## self.gitdir = project.home_#Nem jo mert ha megosztottak a projektet, akkor a projekttulajdonos konyvtarat jelenti
        self.gitdir = os.path.join(project.mp_git, user.username, project.path_with_namespace.replace('/', '_'))
        d = Docker()
        url = d.get_docker_url()
        self.dockerclient = docker.client.Client(base_url = url)
        self.sshagentsock = os.path.join('/tmp', self.user)
        usercommand = [ "/usr/local/bin/init-ssh-agent.sh", self.user ]
        x = self.dockerclient.exec_create(container = self.container_git, cmd = usercommand)
        self.dockerclient.exec_start(exec_id = x['Id'], stream = False)
        check = self.dockerclient.exec_inspect(exec_id = x['Id'])
        assert check['ExitCode'] == 0, check

    def __execute(self, command):
        usercommand = [ "sudo", "-i", "-u", self.user, "sh", "-c", "cd %s ; SSH_AUTH_SOCK=%s %s" % (self.gitdir, self.sshagentsock, command) ]
        x = self.dockerclient.exec_create(container = self.container_git, cmd = usercommand)
        response = self.dockerclient.exec_start(exec_id = x['Id'], stream = False)
        check = self.dockerclient.exec_inspect(exec_id = x['Id'])
        assert check['ExitCode'] == 0, check
        return response

    def log(self):
        tags = [ 'commitid', 'name', 'message', 'date', 'time' ]
        regexp = r"""commit (?P<commitid>[0-9a-z]{40})
Author: (?P<name>[A-Za-z\ \.]+)\s<[a-z0-9\.\-_]+@[a-z0-9\.]+>
Date:   (?P<date>\d{4}-\d{2}-\d{2})\s(?P<time>\d{2}:\d{2}:\d{2}).*

\s*(?P<message>.*)\s*
"""
        command = "git log --date iso8601"
        resp = self.__execute(command).decode()
        log_list = [ dict(map(lambda k: (k, m.group(k)), tags)) for m in re.finditer(regexp, resp) ]
        assert len(log_list), "Empty log"
        return log_list

    def _lsfiles(self, lstype, extra = ''):
        command = "git ls-files --%s %s" % (lstype, extra)
        return self.__execute(command).decode().splitlines()

    def lsfiles(self):
        files_deleted = self._lsfiles('deleted')
        files_other = self._lsfiles('other', extra = '-x .ipynb_checkpoints')
        files_modified = list(set(self._lsfiles('modified')).difference(set(files_deleted)))
        return { 'modified': files_modified, 'deleted': files_deleted, 'other': files_other }

    def add(self, files):
        command = "git add %s" % " ".join(files)
        return self.__execute(command)

    def remove(self, files):
        command = "git rm %s" % " ".join(files)
        return self.__execute(command)

    def commit(self, message):
        command = "git commit -m '%s'" % (message)
        return self.__execute(command)

    def push(self):
        command = "git push"
        return self.__execute(command)

    def pull(self):
        command = "git pull"
        return self.__execute(command)

    def reset(self):
        command = "git reset"
        return self.__execute(command)

    def revert(self, commitid):
        self.reset()
        history = self.log()
        latestid = history[0]['commitid']
        if latestid != commitid:
            behindid = None
            for x in history:
                if x['commitid'] == commitid:
                    break
                behindid = x['commitid']
            assert behindid is not None, "Commitid %s not found" % commitid
            if behindid != latestid:
                command = "git revert --no-commit %s..%s" % (behindid, latestid)
                self.__execute(command)
        command = "git checkout %s ." % commitid
        self.__execute(command)
        self.commit("Revert \"%s\"" % x['message'])
        self.push()

    def remote_changed(self):
        command = "git ls-remote"
        resp = self.__execute(command).decode()
        _, remoteid, _ = re.split(r'^.*\n?([a-z0-9]{40})\sHEAD\n.*$', resp)
        history = self.log()
        return history[0]['commitid'] != remoteid
