import os
import git

from kooplex.lib import get_settings

#FIXME:
LibBase = object
def print_debug(*v, **w): pass


class RepoException(Exception):
    pass

class Repo(LibBase):

    def __init__(self, username, name, proto='ssh'):

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
        print_debug("")
        url = LibBase.join_path(self.base_repourl, self.name + '.git')
        return url

    def get_gitlab_ssh(self):
        print_debug("")

        ssh = 'ssh://git@%s:/%s.git' % (self.ssh_host, self.name)
        return ssh

    def get_gitlab_key(self):
        return os.path.join(get_settings('volumes','home'), self.username, self.ssh_key)

    def get_git_ssh_command(self):
        print_debug("")

        key = self.get_gitlab_key()
        key = key.replace('\\', '/')
        cmd = "'%s' -v -i '%s'" % (self.ssh_cmd, key)
        if self.ssh_port != 22:
            cmd = cmd + ' -p %d' % self.ssh_port
        return cmd

    def get_remote_url(self):
        print_debug("")
        if self.proto == 'http':
            return self.get_gitlab_url()
        elif self.proto == 'ssh':
            return self.get_gitlab_ssh()
        else:
            raise NotImplementedError

    def get_local_dir(self):
        print_debug("")
        return os.path.join(self.srv_dir, '_git', self.username, self.name.replace('/', '_'))

    def ensure_local_dir_empty(self):
        print_debug("")
        dir = self.get_local_dir()
        LibBase.ensure_dir(dir)
        LibBase.clean_dir(dir)

    def is_local_existing(self):
        print_debug("")
        dir = self.get_local_dir()
        print("TTT2", dir)
        path = os.path.join(dir, '.git')
        res = os.path.exists(path)
        return res

    def get_local(self):
        print_debug("")
        dir = self.get_local_dir()
        repo = git.Repo(dir)
        return repo

    def init_local(self):
        print_debug("")
        dir = self.get_local_dir()
        repo = git.Repo.init(dir)
        return repo

    def ensure_local(self):
        print_debug("")
        dir = self.get_local_dir()
        LibBase.ensure_dir(dir)
        if not is_local_repo():
            self.ensure_local_dir_empty()
            self.init_local_repo()

    def clone(self):
        print_debug("")
        url = self.get_remote_url()
        dir = self.get_local_dir()
        print("TTT",dir)
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
        print_debug("")
        dir = self.get_local_dir()
        self.ensure_local_dir_empty()
        os.rmdir(dir)

    def commit_and_push_default(self, commit_message, email, project_owner, project_name):
        print_debug("")
        dir = self.get_local_dir()
        print(dir)
        dir = LibBase.join_path(dir, project_owner)
        dir = LibBase.join_path(dir, project_name)
        dir = dir.replace('/', os.path.sep)
        cmd = self.get_git_ssh_command()
        repo = git.Repo(dir)
        #Adding all modified files to stage for commit
        repo.git.add(u=True)
        untracted_list = []
        #Adding nonhidden, untracted files to version control automatically
        for untracted_file in repo.untracked_files:
            if untracted_file[0]!=".":
                untracted_list.append(untracted_file)
        repo.index.add(untracted_list)
        author = git.Actor(self.username, email)
        repo.index.commit(message=commit_message, author=author, committer=author)
        origin = repo.remote()
        with repo.git.custom_environment(GIT_SSH_COMMAND=cmd):
            origin.push()

    def commit_and_push(self, commit_message, email, project_owner, project_name, creator_name,
                        modified_file_list, deleted_file_list):
        print_debug("commit and push ...")

        cmd = self.get_git_ssh_command()
        repo = git.Repo(self.get_local_dir())
        author = git.Actor(self.username, email)
        origin = repo.remote()
        if len(modified_file_list):
              repo.index.add(modified_file_list)
              repo.index.commit(message = commit_message, author = author, committer = author)
              print_debug("modified: " + str(modified_file_list))
              with repo.git.custom_environment(GIT_SSH_COMMAND=cmd):
                  origin.push()
        if len(deleted_file_list):
              commit_message += "\nDeleted: \n\t" + "\n\t".join(deleted_file_list)
              repo.index.remove(deleted_file_list)
              print_debug("removed:" + str(deleted_file_list))
              repo.index.commit(message = commit_message, author = author, committer = author)
              with repo.git.custom_environment(GIT_SSH_COMMAND=cmd):
                  origin.push()

    def list_committable_files(self, path_with_namespace):
        print_debug("")
        dir = self.get_local_dir()
        dir = dir.replace('/', os.path.sep)
        repo = git.Repo(dir)
        deleted_list = []
# Important note: the recently added (new) and renamed files will appear as untrackted files
# because we cannot use adding or renameing function via git on jupyter UI
# so this file types are commented out.
#        new_list = []
#        renamed_list = []
        modified_list = []
        for file in repo.index.diff(None):
            if file.deleted_file:
                deleted_list.append(file.a_path)
#            elif file.new_file:
#                new_list.append(file.b_path)
#            elif file.renamed:
#                renamed_list.append(file.b_path)
            else:
                modified_list.append(file.b_path)
        untracted_list = []
        # Adding nonhidden, untracted files
        for untracted_file in repo.untracked_files:
            if untracted_file[0] != ".":
                untracted_list.append(untracted_file)
#        committable_dict = {"n":new_list,"d":deleted_list,"r":renamed_list,
#                            "m":modified_list,"u":untracted_list}
        committable_dict = {"d": deleted_list, "m": modified_list, "u": untracted_list}
        return committable_dict


