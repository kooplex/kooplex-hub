import os
import ast
import time
import glob
from distutils.dir_util import mkpath, copy_tree, remove_tree
from distutils.file_util import copy_file, move_file

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

def _chown_recursive(path, uid = 0, gid = 0):
    os.chown(path, uid, gid)
    for root, dirs, files in os.walk(path):
        for name in dirs:
            os.chown(os.path.join(root, name), uid, gid)
        for name in files:
            os.chown(os.path.join(root, name), uid, gid)

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
        yield { 'fullpath': fn, 'volume': 'git', 'filename': os.path.basename(fn) }
    pattern_notebooks = os.path.join(get_settings('volumes','share'), project.name_with_owner, '*.ipynb')
    for fn in glob.glob(pattern_notebooks):
        yield { 'fullpath': fn, 'volume': 'share', 'filename': os.path.basename(fn) }
    pattern_notebooks = os.path.join(get_settings('volumes','home'), user.username, '*.ipynb')
    for fn in glob.glob(pattern_notebooks):
        yield { 'fullpath': fn, 'volume': 'home', 'filename': os.path.basename(fn) }

def list_files(user, project):
    def skip(fn):
        if fn.endswith('.ipynb'):
            return True
        if not os.path.isdir(fn):
            return False
        if fn.endswith('git') or fn.endswith('oc') or fn.endswith('share'):
            return True
        return False

    pattern_notebooks = os.path.join(get_settings('volumes','git'), user.username, project.name_with_owner, '*')
    for fn in glob.glob(pattern_notebooks):
        if not skip(fn):
            yield { 'fullpath': fn, 'volume': 'git', 'filename': os.path.basename(fn), 'is_dir': os.path.isdir(fn) }
    pattern_notebooks = os.path.join(get_settings('volumes','share'), project.name_with_owner, '*')
    for fn in glob.glob(pattern_notebooks):
        if not skip(fn):
            yield { 'fullpath': fn, 'volume': 'share', 'filename': os.path.basename(fn), 'is_dir': os.path.isdir(fn) }
    pattern_notebooks = os.path.join(get_settings('volumes','home'), user.username, '*')
    for fn in glob.glob(pattern_notebooks):
        if not skip(fn):
            yield { 'fullpath': fn, 'volume': 'home', 'filename': os.path.basename(fn), 'is_dir': os.path.isdir(fn) }

def move_htmlreport_in_place(report):
    from kooplex.hub.models import HtmlReport
    assert isinstance(report, HtmlReport)
    filename_source = report.filename_html
    filename_destination = report.filename_report_html
    folder = os.path.dirname(filename_destination)
    mkpath(folder)
    move_file(filename_source, folder)

def copy_dashboardreport_in_place(report, files):
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
    mkpath(dir_target)
    copy_file(filename_source, dir_target)
    for f in files:
        f = ast.literal_eval(f)
        if f['volume'] == 'home':
            dir_container = '.'
        elif f['volume'] in [ 'git', 'share' ]:
            dir_container = f['volume']
        else:
            continue
        dir_target = os.path.join(report_root, dir_container)
        if f['is_dir']:
            copy_tree(f['fullpath'], os.path.join(dir_target, f['filename']))
        else:
            mkpath(dir_target)
            copy_file(f['fullpath'], dir_target)
    _chown_recursive(report_root, get_settings('dashboard', 'uid'), get_settings('dashboard', 'gid'))

def cleanup_reportfiles(report):
    from kooplex.hub.models import HtmlReport, DashboardReport
    garbage = os.path.join(get_settings('volumes', 'garbage'), "report.%f" % time.time())
    if isinstance(report, HtmlReport):
        try:
            copy_tree(os.path.dirname(report.filename_report_html), garbage)
            remove_tree(os.path.dirname(report.filename_report_html))
        except:
            raise
    else:
        raise NotImplementedError


