import os
import git

from kooplex.lib import LibBase, get_settings

class RepoException(Exception):
    pass

class Repo(LibBase):

    def __init__(self, username, name, proto='ssh'):

        self.user_home_dir = get_settings('users', 'home_dir')
        self.srv_dir = get_settings('users', 'srv_dir')
        self.base_url = get_settings('gitlab', 'base_url')
        self.ssh_cmd = get_settings('gitlab', 'ssh_cmd', None, 'ssh')
        self.ssh_host = get_settings('gitlab', 'ssh_host')
        self.ssh_port = get_settings('gitlab', 'ssh_port', None, 22)
        self.ssh_key = get_settings('gitlab', 'ssh_key', None, '.ssh/gitlab.key')
        self.ssh_key_password = get_settings('gitlab', 'ssh_key_password')

        self.username = username
        self.name = name
        self.proto = proto # 'http|ssh'

    def get_gitlab_url(self):
        url = LibBase.join_path(self.base_url, self.name + '.git')
        return url

    def get_gitlab_ssh(self):
        ssh = 'ssh://git@%s:/%s.git' % (self.ssh_host, self.name)
        return ssh

    def get_gitlab_key(self):
        home = self.user_home_dir.replace('{$username}', self.username)
        key = os.path.join(self.srv_dir, home)
        key = os.path.join(key, self.ssh_key)
        return key

    def get_git_ssh_command(self):
        key = self.get_gitlab_key()
        key = key.replace('\\', '/')
        cmd = "'%s' -v -i '%s'" % (self.ssh_cmd, key)
        if self.ssh_port != 22:
            cmd = cmd + ' -p %d' % self.ssh_port
        return cmd

    def get_remote_url(self):
        if self.proto == 'http':
            return self.get_gitlab_url()
        elif self.proto == 'ssh':
            return self.get_gitlab_ssh()
        else:
            raise NotImplementedError

    def get_local_dir(self):
        home = self.user_home_dir.replace('{$username}', self.username)
        dir = LibBase.join_path(self.srv_dir, home)
        dir = LibBase.join_path(dir, 'projects')
        dir = LibBase.join_path(dir, self.name)
        dir = dir.replace('/', os.path.sep)
        return dir        

    def ensure_local_dir_empty(self):
        dir = self.get_local_dir()
        LibBase.ensure_dir(dir)
        LibBase.clean_dir(dir)

    def is_local_existing(self):
        dir = self.get_local_dir()
        path = os.path.join(dir, '.git')
        res = os.path.exists(path)
        return res

    def get_local(self):
        dir = self.get_local_dir()
        repo = git.Repo(dir)
        return repo

    def init_local(self):
        dir = self.get_local_dir()
        repo = git.Repo.init(dir)
        return repo

    def ensure_local(self):
        dir = self.get_local_dir()
        LibBase.ensure_dir(dir)
        if not is_local_repo():
            self.ensure_local_dir_empty()
            self.init_local_repo()

    def clone(self):
        url = self.get_remote_url()
        dir = self.get_local_dir()
        cmd = self.get_git_ssh_command()
        repo = git.Repo.clone_from(url, dir, env=dict(GIT_SSH_COMMAND=cmd))
        return repo
            

        #g = git.Git()
        #remote = repo.create_remote('origin', url)
        ## This requires git 2.7 or newer!
        #cmd = git.repo.git.self.get_git_ssh_command()
        #with g.custom_environment(GIT_SSH_COMMAND=cmd):
        #    #dir = dir.replace('\\', '/')
        #    #repo = git.Repo.clone_from(url, dir)
        #    return repo

    def delete_local(self):
        dir = self.get_local_dir()
        self.ensure_local_dir_empty()
        os.rmdir(dir)
