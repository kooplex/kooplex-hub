import os
from distutils.dir_util import mkpath

from kooplex.lib.libbase import get_settings

def mkdir_davsecret(user):
    dir_secret = os.path.join(get_settings('volumes', 'home'), user.username, '.davfs2')
    mkpath(dir_secret)
    os.chown(dir_secret, user.uid, user.gid)
    os.chmod(dir_secret, 0b111000000)

def write_davsecret(user):
    mkdir_davsecret(user)
    fn_secret = os.path.join(get_settings('volumes', 'home'), user.username, '.davfs2', 'secrets')
    with open(fn_secret, "w") as f:
        f.write(os.path.join(get_settings('owncloud', 'inner_url'), "remote.php/webdav/") + " %s %s" % (user.username, user.password))
    os.chown(fn_secret, user.uid, user.gid)
    os.chmod(fn_secret, 0b110000000)

