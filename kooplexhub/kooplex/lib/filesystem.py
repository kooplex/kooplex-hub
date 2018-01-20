"""
@autor: Jozsef Steger
@summary: file and directory operations
"""
import logging
import os
import ast
import time
import glob
import subprocess
from distutils import dir_util
from distutils import file_util

from kooplex.lib import get_settings, bash

logger = logging.getLogger(__name__)
G_OFFSET = 20000

def _mkdir(path, uid = 0, gid = 0, mode = 0b111101000, mountpoint = False):
    """
    @summary: make directory, set ownership and mode. (A helper method)
    @param path: the directory to make
    @type path: str
    @param uid: filesystem level user id, default 0
    @type uid: int
    @param gid: filesystem level group id, default 0
    @type gid: int
    @param mode: filesystem access flags (9 bits), default 0b111101000
    @type mode: int
    @param mountpoint: whether the created directory is to be used as a mount point, default False
    @typa mountpoint: bool
    """
    logger.debug("dir: %s uid/gid: %d/%d; mountpoint: %s" % (d, uid, gid, mountpoint))
    dir_util.mkpath(path)
    os.chown(path, uid, gid)
    os.chmod(path, mode)
    if mountpoint:
        placeholder = os.path.join(path, '.notmounted')
        open(placeholder, 'w').close()
        os.chown(placeholder, 0, 0)
        os.chmod(placeholder, 0)

def _mkdir_davsecret(user):
    dir_secret = os.path.join(get_settings('volumes', 'home'), user.username, '.davfs2')
    _mkdir(dir_secret, user.uid, user.gid, 0b111000000)
    return dir_secret

def _chown_recursive(path, uid = 0, gid = 0):
    logger.debug("dir: %s uid/gid: %d/%d" % (d, uid, gid))
    os.chown(path, uid, gid)
    for root, dirs, files in os.walk(path):
        for name in dirs:
            os.chown(os.path.join(root, name), uid, gid)
        for name in files:
            os.chown(os.path.join(root, name), uid, gid)

def write_davsecret(user):
    """
    @summary: owncloud module requires the password for davfs mount, so we store it
    @param user: the user
    @type user: kooplex.hub.models.User
    """
    logger.debug(user)
    dir_secret = _mkdir_davsecret(user)
    fn_secret = os.path.join(dir_secret, 'secrets')
    with open(fn_secret, 'w') as f:
        f.write(get_settings('user', 'pattern_davsecret') % user)
    os.chown(fn_secret, user.uid, user.gid)
    os.chmod(fn_secret, 0b110000000)

def write_gitconfig(user):
    """
    @summary: store the configuration of the git command line client tool
    @param user: the user
    @type user: kooplex.hub.models.User
    """
    logger.debug(user)
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
    """
    @summary: generate an RSA key pair for a given user to access version control repository
    @param user: the user
    @type user: kooplex.hub.models.User
    @param overwrite: whether to overwrite any existing files, dafault False
    @type overwrite: bool
    """
    logger.debug("%s, overwrite %s" % (user, overwrite))
    dir_ssh = os.path.join(get_settings('volumes', 'home'), user.username, '.ssh')
    _mkdir(dir_ssh, uid = user.uid, gid = user.gid, mode = 0b111000000)
    fn_keyfile = os.path.join(dir_ssh, "gitlab.key")
    if not overwrite and os.path.exists(fn_keyfile):
        return
    bash('/usr/bin/ssh-keygen -N -f %s' % fn_keyfile)
    os.chown(key_fn, user.uid, user.gid)
    os.chown(key_fn + ".pub", user.uid, user.gid)

def read_rsapubkey(user):
    """
    @summary: read the public RSA key of a user
    @param user: the user
    @type user: kooplex.hub.models.User
    """
    fn_keyfile = os.path.join(get_settings('volumes', 'home'), user.username, '.ssh', 'gitlab.key.pub')
    return open(fn_keyfile).read().strip()

def mkdir_homefolderstructure(user):
    """
    @summary: create a home directory for the user
    @param user: the user
    @type user: kooplex.hub.models.User
    """
    logger.info(user)
    dir_home = os.path.join(get_settings('volumes', 'home'), user.username)
    _mkdir(dir_home, uid = user.uid, gid = user.gid)
    dir_oc = os.path.join(get_settings('volumes', 'home'), user.username, 'oc')
    _mkdir(dir_oc, mountpoint = True)
    dir_git = os.path.join(get_settings('volumes', 'home'), user.username, 'git')
    _mkdir(dir_git, mountpoint = True)
    write_davsecret(user)
    write_gitconfig(user)
    generate_rsakey(user)

def cleanup_home(user):
    """
    @summary: move user's data on the garbage volume
              1. move home directory
              2. move share directory
              3. move git working directory
    @param user: user whose data are moved
    @type user: kooplex.hub.models.User
    returns success flags:
              0: success
              0x001: error moving home
              0x010: error moving share
              0x100: error moving git
    """
    logger.info(user)
    garbage = os.path.join(get_settings('volumes', 'garbage'), "user-%s.%f" % (user.username, time.time()))
    dir_util.mkpath(garbage)
    status = 0
    try:
        dir_home = os.path.join(get_settings('volumes', 'home'), user.username)
        dir_util.copy_tree(dir_home, garbage)
        dir_util.remove_tree(os.path.dirname(dir_home))
        logger.info("moved %s -> %s" % (dir_home, garbage))
    except Exception as e:
        status |= 0x001
        logger.error("cannot move %s (%s)" % (dir_home, e))
    try:
        dir_share = os.path.join(get_settings('volumes', 'share'), user.username)
        dir_util.copy_tree(dir_share, garbage)
        dir_util.remove_tree(os.path.dirname(dir_share))
        logger.info("moved %s -> %s" % (dir_share, garbage))
    except Exception as e:
        status |= 0x010
        logger.error("cannot move %s (%s)" % (dir_share, e))
    try:
        dir_git = os.path.join(get_settings('volumes', 'git'), user.username)
        dir_util.copy_tree(dir_git, garbage)
        dir_util.remove_tree(os.path.dirname(dir_git))
        logger.info("moved %s -> %s" % (dir_git, garbage))
    except Exception as e:
        status |= 0x100
        logger.error("cannot move %s (%s)" % (dir_git, e))
    return status

def mkdir_project(user, project):
    """
    @summary: create working directories for the project
            1. subversion control working directory
            2. share directory
    @param user: user of the project
    @type user: kooplex.hub.models.User
    @param project: the project
    @type project: kooplex.hub.models.Project
    """
    folder_git = os.path.join(get_settings('volumes','git'), user.username, project.name_with_owner)
    _mkdir(folder_git, user.uid, G_OFFSET + project.id, 0b111100000)
    folder_share = os.path.join(get_settings('volumes','share'), project.name_with_owner)
    _mkdir(folder_share, project.owner.uid, G_OFFSET + project.id, 0b111111101)

def list_notebooks(user, project):
    """
    @summary: iterate over user files with ipynb extension
            1. loop over git working directory
            2. loop over project share
            3. loop over home directory
    @param user: the user
    @type user: kooplex.hub.models.User
    @param project: the project
    @type project: kooplex.hub.models.Project
    """
    pattern_notebooks = os.path.join(get_settings('volumes','git'), user.username, project.name_with_owner, '*.ipynb')
    for fn in glob.glob(pattern_notebooks):
        yield { 'fullpath': fn, 'volume': 'git', 'filename': os.path.basename(fn) }
    pattern_notebooks = os.path.join(get_settings('volumes','share'), project.name_with_owner, '*.ipynb')
    for fn in glob.glob(pattern_notebooks):
        yield { 'fullpath': fn, 'volume': 'share', 'filename': os.path.basename(fn) }
    pattern_notebooks = os.path.join(get_settings('volumes','home'), user.username, '*.ipynb')
    for fn in glob.glob(pattern_notebooks):
        yield { 'fullpath': fn, 'volume': 'home', 'filename': os.path.basename(fn) }

def list_files(user, project):
    """
    @summary: iterate over user files with not an ipynb extension and also directories
            1. loop over git working directory
            2. loop over project share
            3. loop over home directory
    @param user: the user
    @type user: kooplex.hub.models.User
    @param project: the project
    @type project: kooplex.hub.models.Project
    """
    def skip(fn):
        if fn.endswith('.ipynb'):
            return True
        if not os.path.isdir(fn):
            return False
        if fn.endswith('git') or fn.endswith('oc') or fn.endswith('share'):
            return True
        return False

    pattern_all = os.path.join(get_settings('volumes','git'), user.username, project.name_with_owner, '*')
    for fn in glob.glob(pattern_all):
        if not skip(fn):
            yield { 'fullpath': fn, 'volume': 'git', 'filename': os.path.basename(fn), 'is_dir': os.path.isdir(fn) }
    pattern_all = os.path.join(get_settings('volumes','share'), project.name_with_owner, '*')
    for fn in glob.glob(pattern_all):
        if not skip(fn):
            yield { 'fullpath': fn, 'volume': 'share', 'filename': os.path.basename(fn), 'is_dir': os.path.isdir(fn) }
    pattern_all = os.path.join(get_settings('volumes','home'), user.username, '*')
    for fn in glob.glob(pattern_all):
        if not skip(fn):
            yield { 'fullpath': fn, 'volume': 'home', 'filename': os.path.basename(fn), 'is_dir': os.path.isdir(fn) }

def move_htmlreport_in_place(report):
    """
    @summary: move report html file in server working directory
    @param report: the report
    @type report: kooplex.hub.models.HtmlReport
    """
    from kooplex.hub.models import HtmlReport
    assert isinstance(report, HtmlReport)
    filename_source = report.filename_html
    filename_destination = report.filename_report_html
    folder = os.path.dirname(filename_destination)
    dir_util.mkpath(folder)
    file_util.move_file(filename_source, folder)

def copy_dashboardreport_in_place(report, files):
    """
    @summary: copy notebook file and its attachments in server working directory
    @param report: the report
    @type report: kooplex.hub.models.DashboardReport
    @param files: attachments a serialized dictionary
    @type files: str
    """
    from kooplex.hub.models import DashboardReport
    assert isinstance(report, DashboardReport)
    filename_source = report.notebook_filename
    report_root = report.report_root
    if filename_source.startswith(get_settings('volumes', 'home')):
        dir_target = report.report_root
    elif filename_source.startswith(get_settings('volumes', 'git')):
        dir_target = os.path.join(report.report_root, 'git')
    elif filename_source.startswith(get_settings('volumes', 'share')):
        dir_target = os.path.join(report.report_root, 'share')
    else:
        raise NotImplementedError
    dir_util.mkpath(dir_target)
    file_util.copy_file(filename_source, dir_target)
    for f in files:
        f = ast.literal_eval(f) #FIXME: evaluate already in the caller
        if f['volume'] == 'home':
            dir_container = '.'
        elif f['volume'] in [ 'git', 'share' ]:
            dir_container = f['volume']
        else:
            continue
        dir_target = os.path.join(report_root, dir_container)
        if f['is_dir']:
            dir_util.copy_tree(f['fullpath'], os.path.join(dir_target, f['filename']))
        else:
            dir_util.mkpath(dir_target)
            file_util.copy_file(f['fullpath'], dir_target)
    _chown_recursive(report_root, get_settings('dashboard', 'uid'), get_settings('dashboard', 'gid'))

def cleanup_reportfiles(report):
    """
    @summary: move report files in garbage volume
    @param report: the report
    @type report: kooplex.hub.models.HtmlReport or kooplex.hub.models.DashboardReport
    """
    from kooplex.hub.models import HtmlReport, DashboardReport
    garbage = os.path.join(get_settings('volumes', 'garbage'), "report.%f" % time.time())
    if isinstance(report, HtmlReport):
        try:
            dir_util.copy_tree(os.path.dirname(report.filename_report_html), garbage)
            dir_util.remove_tree(os.path.dirname(report.filename_report_html))
        except:
            raise
    else:
        raise NotImplementedError


