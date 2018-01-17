import os
import glob
from distutils.dir_util import mkpath

from kooplex.lib import get_settings

G_OFFSET = 20000

def _mkdir(d, uid = 0, gid = 0, mode = 0b111101000, mountpoint = False):
    mkpath(d)
    os.chown(d, uid, gid)
    os.chmod(d, mode)
    if mountpoint:
        placeholder = os.path.join(d, '.notmounted')
        open(placeholder, 'w').close()
        os.chown(placeholder, 0, 0)
        os.chmod(placeholder, 0)

def _mkdir_davsecret(user):
    dir_secret = os.path.join(get_settings('volumes', 'home'), user.username, '.davfs2')
    _mkdir(dir_secret, user.uid, user.gid, 0b111000000)
    return dir_secret

def write_davsecret(user):
    dir_secret = _mkdir_davsecret(user)
    fn_secret = os.path.join(dir_secret, 'secrets')
    with open(fn_secret, 'w') as f:
        f.write(get_settings('user', 'pattern_davsecret') % user)
    os.chown(fn_secret, user.uid, user.gid)
    os.chmod(fn_secret, 0b110000000)

def write_gitconfig(user):
    fn_gitconfig = os.path.join(get_settings('volumes', 'home'), user.username, '.gitconfig')
    with open(fn_gitconfig, 'w') as f:
        f.write("""
[user]
        name = %s %s
        email = %s
[push]
        default = matching
""" % (user.first_name, user.last_name, user.email))
    os.chown(fn_gitconfig, user.uid, user.gid)
    os.chmod(fn_gitconfig, 0b110000000)

def generate_rsakey(user, overwrite = False):
    dir_ssh = os.path.join(get_settings('volumes', 'home'), user.username, '.ssh')
    _mkdir(dir_ssh, uid = user.uid, gid = user.gid, mode = 0b111000000)
    fn_keyfile = os.path.join(dir_ssh, "gitlab.key")
    if not overwrite and os.path.exists(fn_keyfile):
        return
    subprocess.call(['/usr/bin/ssh-keygen', '-N', '', '-f', fn_keyfile])
    os.chown(key_fn, user.uid, user.gid)
    os.chown(key_fn + ".pub", user.uid, user.gid)

def read_rsapubkey(user):
    fn_keyfile = os.path.join(get_settings('volumes', 'home'), user.username, '.ssh', 'gitlab.key.pub')
    return open(fn_keyfile + ".pub").read().strip()

def mkdir_homefolderstructure(user):
    dir_home = os.path.join(get_settings('volumes', 'home'), user.username)
    _mkdir(dir_home, uid = user.uid, gid = user.gid)
    dir_oc = os.path.join(get_settings('volumes', 'home'), user.username, 'oc')
    _mkdir(dir_oc, mountpoint = True)
    dir_git = os.path.join(get_settings('volumes', 'home'), user.username, 'git')
    _mkdir(dir_git, mountpoint = True)
    write_davsecret(user)
    write_gitconfig(user)
    generate_rsakey(user)

def mkdir_project(user, project):
    folder_git = os.path.join(get_settings('volumes','git'), user.username, project.name_with_owner)
    _mkdir(folder_git, user.uid, G_OFFSET + project.id, 0b111100000)
    folder_share = os.path.join(get_settings('volumes','share'), project.name_with_owner)
    _mkdir(folder_share, project.owner.uid, G_OFFSET + project.id, 0b111111101)

def list_notebooks(user, project):
    pattern_notebooks = os.path.join(get_settings('volumes','git'), user.username, project.name_with_owner, '*.ipynb')
    for fn in glob.glob(pattern_notebooks):
        yield fn, 'git', os.path.basename(fn)
    pattern_notebooks = os.path.join(get_settings('volumes','share'), project.name_with_owner, '*.ipynb')
    for fn in glob.glob(pattern_notebooks):
        yield fn, 'share', os.path.basename(fn)
    pattern_notebooks = os.path.join(get_settings('volumes','home'), user.username, '*.ipynb')
    for fn in glob.glob(pattern_notebooks):
        yield fn, 'home', os.path.basename(fn)

