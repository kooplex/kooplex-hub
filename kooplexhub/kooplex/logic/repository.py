'''
@author: Jozsef Steger
@created: 25. 07. 2017
@summary: issue git commands in favor of a user inside a docker contaner
'''

import logging
import os
import re

from kooplex.lib import get_settings, Docker
from .impersonator import get_impersonator_container

logger = logging.getLogger(__name__)

class NotCheckedOut(Exception):
    pass

class Repository:

    def __init__(self, user, project):
        self.user = user
        self.project = project
        self.container = get_impersonator_container()
        self.docker = Docker()

        command = "ls ~/git/.git"
        response = self.docker.execute2(self.container, command)
        if self.docker.check['ExitCode'] == 2:
            raise NotCheckedOut(response)

        command = '/usr/local/bin/init-ssh-agent.sh %s' % self.user.username
        self.docker.execute2(self.container, command)
        logger.debug('initialized repo: user: %s, project: %s' % (user, project))

    @property
    def sshagentsock(self):
        return os.path.join('/tmp', self.user.username)

    @property
    def gitdir(self):
        return os.path.join(get_settings('impersonator', 'git'), self.user.username, self.project.name_with_owner)


    def _sudowrap(self, command):
        return 'sudo -i -u %s sh -c "cd %s ; SSH_AUTH_SOCK=%s %s"' % (self.user.username, self.gitdir, self.sshagentsock, command)

    def log(self):
        logger.debug('user: %s, project: %s' % (self.user, self.project))
        tags = [ 'commitid', 'name', 'message', 'date', 'time' ]
        regexp = r"""commit (?P<commitid>[0-9a-z]{40})
Author: (?P<name>[A-Za-z\ \.]+)\s<[a-z0-9\.\-_]+@[a-z0-9\.]+>
Date:   (?P<date>\d{4}-\d{2}-\d{2})\s(?P<time>\d{2}:\d{2}:\d{2}).*

\s*(?P<message>.*)\s*
"""
        command = self._sudowrap("git log --date iso8601")
        resp = self.docker.execute2(self.container, command)
        log_list = [ dict(map(lambda k: (k, m.group(k)), tags)) for m in re.finditer(regexp, resp) ]
        return log_list

    def _lsfiles(self, lstype, extra = ''):
        command = self._sudowrap("git ls-files --%s %s" % (lstype, extra))
        return self.docker.execute2(self.container, command).splitlines()

    def lsfiles(self):
        logger.debug('user: %s, project: %s' % (self.user, self.project))
        files_deleted = self._lsfiles('deleted')
        files_other = self._lsfiles('other', extra = '-x .ipynb_checkpoints')
        files_modified = list(set(self._lsfiles('modified')).difference(set(files_deleted)))
        return { 'modified': files_modified, 'deleted': files_deleted, 'other': files_other }

    def remote_changed(self):
        logger.debug('user: %s, project: %s' % (self.user, self.project))
        command = self._sudowrap("git ls-remote")
        resp = self.docker.execute2(self.container, command)
        _, remoteid, _ = re.split(r'([a-f0-9]{40})\sHEAD', resp)
        history = self.log()
        return history[0]['commitid'] != remoteid

    def add(self, files):
        if not len(files): return
        logger.debug("%d files" % len(files))
        command = self._sudowrap("git add %s" % " ".join(files))
        return self.docker.execute2(self.container, command)

    def remove(self, files):
        if not len(files): return
        logger.debug("%d files" % len(files))
        command = self._sudowrap("git rm %s" % " ".join(files))
        return self.docker.execute2(self.container, command)

    def commit(self, message):
        logger.info("project %s user %s commit %s" % (self.project, self. user, message))
        command = self._sudowrap("git commit -m '%s'" % (message))
        return self.docker.execute2(self.container, command)

    def push(self):
        logger.debug('user: %s, project: %s' % (self.user, self.project))
        command = self._sudowrap("git push")
        return self.docker.execute2(self.container, command)

    def pull(self):
        logger.debug('user: %s, project: %s' % (self.user, self.project))
        command = self._sudowrap("git pull")
        return self.docker.execute2(self.container, command)

    def reset(self):
        logger.debug('user: %s, project: %s' % (self.user, self.project))
        command = self._sudowrap("git reset")
        return self.docker.execute2(self.container, command)

    def revert(self, commitid):
        logger.debug('user: %s, project: %s' % (self.user, self.project))
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
        command = self._sudowrap("git checkout %s ." % commitid)
        self.docker.execute2(self.container, command)
        if latestid != commitid:
            self.commit("Revert \"%s\"" % x['message'])
            self.push()

