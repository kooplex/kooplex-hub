"""
@autor: Jozsef Steger
@summary: file and directory operations
"""
import re
import logging
import os
import ast
import time
import glob
import base64
from distutils import dir_util
from distutils import file_util

from kooplex.lib import get_settings, bash

logger = logging.getLogger(__name__)

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
    logger.debug("dir: %s uid/gid: %d/%d; mountpoint: %s" % (path, uid, gid, mountpoint))
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
    logger.debug("dir: %s uid/gid: %d/%d" % (path, uid, gid))
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
    bash('/usr/bin/ssh-keygen -N "" -f %s' % fn_keyfile)
    os.chown(fn_keyfile, user.uid, user.gid)
    os.chown(fn_keyfile + ".pub", user.uid, user.gid)

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
    _mkdir(dir_oc, mountpoint = True, mode = 0b111101101)
    dir_git = os.path.join(get_settings('volumes', 'home'), user.username, 'git')
    _mkdir(dir_git, mountpoint = True)
    dir_condaenv = os.path.join(get_settings('volumes', 'home'), user.username, '.conda', 'envs')
    _mkdir(dir_condaenv, uid = user.uid, gid = user.gid, mode = 0o700)
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
        dir_util.remove_tree(dir_home)
        logger.info("moved %s -> %s" % (dir_home, garbage))
    except Exception as e:
        status |= 0x001
        logger.error("cannot move %s (%s)" % (dir_home, e))
    for p in user.projects():
        cleanup_share(p)
    try:
        dir_git = os.path.join(get_settings('volumes', 'git'), user.username)
        dir_util.copy_tree(dir_git, garbage)
        dir_util.remove_tree(dir_git)
        logger.info("moved %s -> %s" % (dir_git, garbage))
    except Exception as e:
        status |= 0x100
        logger.error("cannot move %s (%s)" % (dir_git, e))
    return status

def mkdir_share(project):
    """
    @summary: create share directory
    @param project: the project
    @type project: kooplex.hub.models.Project
    """
    folder_share = os.path.join(get_settings('volumes','share'), project.name_with_owner)
    _mkdir(folder_share, project.owner.uid, project.owner.gid, 0b111111101)
    logger.info("created %s" % (folder_share))

def cleanup_share(project):
    """
    @summary: remove share directory to garbage
    @param project: the project
    @type project: kooplex.hub.models.Project
    """
    folder_share = os.path.join(get_settings('volumes','share'), project.name_with_owner)
    garbage = os.path.join(get_settings('volumes', 'garbage'), "share-%s.%f" % (project.name_with_owner, time.time()))
    try:
        dir_util.copy_tree(folder_share, garbage)
        dir_util.remove_tree(folder_share)
        logger.info("moved %s -> %s" % (folder_share, garbage))
    except Exception as e:
        logger.error("cannot move %s (%s)" % (folder_share, e))

def mkdir_git_workdir(user, project):
    """
    @summary: create subversion control working directory
    @param user: user of the project
    @type user: kooplex.hub.models.User
    @param project: the project
    @type project: kooplex.hub.models.Project
    """
    folder_git = os.path.join(get_settings('volumes','git'), user.username, project.name_with_owner)
    _mkdir(folder_git, user.uid, project.owner.gid, 0b111100000)

def cleanup_git_workdir(user, project):
    """
    @summary: move subversion control working directory to garbage volume
    @param user: user of the project
    @type user: kooplex.hub.models.User
    @param project: the project
    @type project: kooplex.hub.models.Project
    """
    folder_git = os.path.join(get_settings('volumes','git'), user.username, project.name_with_owner)
    garbage = os.path.join(get_settings('volumes', 'garbage'), "gitwd-%s-%s.%f" % (user.username, project.name_with_owner, time.time()))
    try:
        dir_util.copy_tree(folder_git, garbage)
        dir_util.remove_tree(folder_git)
        logger.info("moved %s -> %s" % (folder_git, garbage))
    except Exception as e:
        logger.error("cannot move %s (%s)" % (folder_git, e))

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
    mkdir_git_workdir(user, project)
    mkdir_share(project)

def _get_mountpoint_in_hub(volname, user, project):
    if volname == 'git':
        return os.path.join(get_settings('volumes','git'), user.username, project.name_with_owner)
    if volname == 'share':
        return os.path.join(get_settings('volumes','share'), project.name_with_owner)
    if volname == 'home':
        return os.path.join(get_settings('volumes','home'), user.username)

def _get_mountpoint_in_container(volname, user):
    if volname == 'git':
        return os.path.join('home', user.username, 'git')
    if volname == 'share':
        return os.path.join('home', user.username, 'share')
    if volname == 'home':
        return os.path.join('home', user.username)

def _filename_in_mount(mountpoint_in_hub, filename_in_hub):
    filename_in_container = filename_in_hub.replace(mountpoint_in_hub, '')
    return filename_in_container[1:] if filename_in_container[0] == '/' else filename_in_container

def _filetype(filename_in_hub):
    if os.path.isdir(filename_in_hub):
        return 'd'
    if os.path.isfile(filename_in_hub):
        return 'f'
    if os.path.islink(filename_in_hub):
        return 'l'

def myencode(filename):
    return base64.b64encode(filename.encode()).decode()

def mydecode(filename_enc):
    return base64.b64decode(filename_enc.encode()).decode()

def translate(representation):
    _, volname, filetype, filename_in_hub_enc, filename_in_container_enc, filename_in_mount, _ = re.split(r'(\w+):(\w):([=\w]+):([=\w]+):(.*)', representation)
    return {
        'filename_in_hub': mydecode(filename_in_hub_enc),
        'filename_in_container': mydecode(filename_in_container_enc),
        'filename_in_mount': filename_in_mount,
        'filetype': filetype,
        'volname': volname,
    }

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
    for volname in [ 'git', 'share', 'home' ]:
        mph = _get_mountpoint_in_hub(volname, user, project)
        mpc = _get_mountpoint_in_container(volname, user)
        for fnh in glob.glob(os.path.join(mph, '*.ipynb')):
            fnm = _filename_in_mount(mph, fnh)
            fnc = os.path.join(mpc, fnm)
            t = _filetype(fnh)
            yield {
                'volume': volname, 
                'isdir': t == 'd', 
                'filename': fnc, 
                'representation': "%s:%s:%s:%s:%s" % (volname, t, myencode(fnh), myencode(fnc), fnm)
            }

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
        if fn.endswith('git') or fn.endswith('oc') or fn.endswith('share') or fn.endswith('__pycache__'):
            return True
        return False

    for volname in [ 'git', 'share', 'home' ]:
        mph = _get_mountpoint_in_hub(volname, user, project)
        mpc = _get_mountpoint_in_container(volname, user)
        for fnh in glob.glob(os.path.join(mph, '*')):
            if not skip(fnh):
                fnm = _filename_in_mount(mph, fnh)
                fnc = os.path.join(mpc, fnm)
                t = _filetype(fnh)
                yield {
                    'volume': volname, 
                    'isdir': t == 'd', 
                    'filename': fnc, 
                    'representation': "%s:%s:%s:%s:%s" % (volname, t, myencode(fnh), myencode(fnc), fnm)
                }

def move_htmlreport_in_place(report):
    """
    @summary: move report html file in server working directory
    @param report: the report
    @type report: kooplex.hub.models.HtmlReport
    """
    from kooplex.hub.models import HtmlReport
    assert isinstance(report, HtmlReport)
    filename_wo_ext, _ = os.path.splitext(report.filename_in_hub)
    filename_source = filename_wo_ext + '.html'
    filename_destination = report.filename_report_html
    folder = os.path.dirname(filename_destination)
    dir_util.mkpath(folder)
    file_util.move_file(filename_source, folder)
    logger.info('Report %s -> %s' % (report, folder))

def copy_reportfiles_in_place(report, files):
    """
    @summary: copy notebook file and its attachments in server working directory
    @param report: the report
    @type report: kooplex.hub.models.DashboardReport
    @param files: attachments a serialized dictionary
    @type files: str
    """
    from kooplex.hub.models import DashboardReport
    report_root = report.report_root
    if isinstance(report, DashboardReport):
        filename_source = report.filename_in_hub
        filename_in_container = report.filename_in_container
        dir_target = os.path.join(report_root, os.path.dirname(filename_in_container))
        dir_util.mkpath(dir_target)
#    file_util.copy_file(filename_source, dir_target)
        target_file = os.path.join(dir_target, os.path.basename(filename_source))
        prepare_dashboardreport_withinitcell(filename_source, target_file)
        logger.debug('convert %s -> %s' % (filename_source, dir_target))
    for f in files:
        t = translate(f)
        dir_target = os.path.join(report_root, os.path.dirname(t['filename_in_container']))
        dir_util.mkpath(dir_target)
        file_util.copy_file(t['filename_in_hub'], dir_target)
        logger.debug('cp %s -> %s' % (t['filename_in_hub'], dir_target))
    _chown_recursive(report_root, get_settings('ldap', 'reportuid'), get_settings('ldap', 'reportgid'))
    logger.info('Report %s -> %s' % (report, report_root))

def prepare_dashboardreport_withinitcell(source_file, target_file):
    import json
    d = json.load(open(source_file))
    for ic in range(len(d['cells'])):
        d['cells'][ic]['metadata']['init_cell'] = True
    d['metadata']['celltoolbar'] = 'Initialization Cell'
    json.dump(d, open(target_file, 'w'))

def cleanup_reportfiles(report):
    """
    @summary: move report files in garbage volume
    @param report: the report
    @type report: kooplex.hub.models.HtmlReport or kooplex.hub.models.DashboardReport
    """
    from kooplex.hub.models import HtmlReport, DashboardReport
    garbage = os.path.join(get_settings('volumes', 'garbage'), "report.%f" % time.time())
    if isinstance(report, HtmlReport):
        move_folder = os.path.dirname(report.filename_report_html)
    elif isinstance(report, DashboardReport):
        move_folder = report.report_root
    else:
        raise NotImplementedError
    try:
        dir_util.copy_tree(move_folder, garbage)
        dir_util.remove_tree(move_folder)
        logger.info("cleanup report %s %s -> %s" % (report, move_folder, garbage))
    except Exception as e:
        logger.error("fail to cleanup report %s %s -> %s -- %s" % (report, move_folder, garbage, e))
        raise

def create_clone_script(project, collaboratoruser = None, project_template = None):
    '''
    @summary: create a magic script to clone the project sources from gitlab
    '''
    if project_template is not None:
        commitmsg = "Snapshot commit of project %s" % project_template.name_with_owner
        script = """#! /bin/bash
rm $0
TMPFOLDER=$(mktemp -d)
git clone %(url)s ${TMPFOLDER}
cd ${TMPFOLDER}
rm -rf ./.git/
mv * /%(gitdir)s
for hidden in $(echo .?* | sed s/'\.\.'//) ; do
  mv $hidden /%(gitdir)s
done
cd /%(gitdir)s
git add --all
git commit -a -m "%(message)s"
git push origin master
rm -rf ${TMPFOLDER}
        """ % { 'url': project_template.url_gitlab, 'message': commitmsg, 'gitdir': _get_mountpoint_in_container('git', project.owner) }
    else:
        user = project.owner if collaboratoruser is None else collaboratoruser
        script = """#! /bin/bash
rm $0
git clone %(url)s /%(gitdir)s
        """ % { 'url': project.url_gitlab, 'gitdir': _get_mountpoint_in_container('git', user)  }
    filename = os.path.join(_get_mountpoint_in_hub('git', user, project), 'clone.sh')
    with open(filename, 'w') as f:
        f.write(script)
    os.chown(filename, user.uid, user.gid)
    os.chmod(filename, 0b111000000)
