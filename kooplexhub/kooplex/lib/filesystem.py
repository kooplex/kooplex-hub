import os
from distutils.dir_util import mkpath

from kooplex.lib import get_settings

G_OFFSET = 20000

def _mkdir(d, uid = 0, gid = 0, mode = 0b111101000):
    mkpath(d)
    os.chown(d, uid, gid)
    os.chmod(d, mode)

def mkdir_project(user, project):
    folder_git = os.path.join(get_settings('volumes','git'), user.username, project.name_with_owner)
    _mkdir(folder_git, user.uid, G_OFFSET + project.id, 0b111100000)
    folder_share = os.path.join(get_settings('volumes','share'), project.name_with_owner)
    _mkdir(folder_share, project.owner.uid, G_OFFSET + project.id, 0b111111101)

def mkdir_davsecret(user):
    dir_secret = os.path.join(get_settings('volumes', 'home'), user.username, '.davfs2')
    _mkdir(dir_secret, user.uid, user.gid, 0b111000000)
    return dir_secret

def write_davsecret(user):
    dir_secret = mkdir_davsecret(user)
    fn_secret = os.path.join(dir_secret, 'secrets')
    with open(fn_secret, "w") as f:
        f.write(get_settings('user', 'pattern_davsecret') % user)
    os.chown(fn_secret, user.uid, user.gid)
    os.chmod(fn_secret, 0b110000000)

