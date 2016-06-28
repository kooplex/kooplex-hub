import os
from git import Repo

from kooplex.lib import LibBase, get_settings

class Git(LibBase):

    def __init__(self, username):
        self.username = username
        self.user_home_dir = get_settings('KOOPLEX_USERS', 'home_dir')
        self.srv_dir = get_settings('KOOPLEX_USERS', 'srv_dir')
        self.gitlab_base_url = get_settings('KOOPLEX_GITLAB', 'base_url')

    def get_repo_name(self, repo):
        if type(repo) is str:
            return repo
        else:
            return repo.name

    def get_remote_url(self, repo):
        name = self.get_repo_name(repo)
        url = LibBase.join_path(self.gitlab_base_url, name + '.git')
        return url

    def get_local_dir(self, repo):
        name = self.get_repo_name(repo)
        home = self.user_home_dir.replace('{$username}', self.username)
        path = LibBase.join_path(self.srv_dir, home)
        path = LibBase.join_path(path, 'projects')
        path = LibBase.join_path(path, name)
        path = path.replace('/', os.path.sep)
        return path

    def ensure_local_dir_empty(self, repo):
        dir = self.get_local_dir(repo)
        LibBase.ensure_dir(dir)
        LibBase.clean_dir(dir)

    def get_repo(self, repo):
        dir = self.get_local_dir(repo)
        LibBase.ensure_dir(dir)
        repo = Repo(dir)
        repo.name = name
        return repo

    def clone_repo(self, repo):
        dir = self.get_local_dir(repo)
        assert dir.find(self.srv_dir) >= 0
        self.ensure_local_dir_empty(dir)
        repo.clone(dir)

    def delete_clone(self, repo):
        pass