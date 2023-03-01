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
from pwd import getpwnam
from grp import getgrnam
from distutils import dir_util
from distutils import file_util
import tarfile

from kooplexhub.settings import KOOPLEX
from kooplexhub.lib import bash
from ..lib import dirname, filename

logger = logging.getLogger(__name__)

acl_backend = KOOPLEX.get('fs_backend', 'nfs4')

try:
    hub = getpwnam('hub')
    hub_uid = hub.pw_uid
    hub_gid = hub.pw_gid
except KeyError:
    logger.warning("hub user is not resolved")
    hub_uid = 0
    hub_gid = 0

try:
    users = getgrnam('users')
    users_gid = users.gr_gid
except KeyError:
    logger.warning("users group is not resolved")
    users_gid = 1000

assert acl_backend in [ 'nfs4', 'posix' ], "Only 'nfs4' and 'posix' acl_backends are supported"


def _count_files(path):
    n = 0
    for _, _, f in os.walk(path):
        n += len(f)
    return n


def _du(path):
    n = 0
    for d, _, fs in os.walk(path):
        for f in fs:
            s = os.stat(os.path.join(d, f))
            n += s.st_size
    return n



def _mkdir(path, other_rx = False):
    """
    @summary: make a directory
    @param path: the directory to make
    @type path: str
    """
    existed = os.path.isdir(path)
    if not existed:
        assert not os.path.exists(path), f"{path} is present in the filesystem, but not a directory"
        dir_util.mkpath(path)
#        assert os.path.isdir(path), f"{path} directory not created"
        rx = 'rx' if other_rx else ''
        if acl_backend == 'nfs4':
            acl = f"""
A::OWNER@:rwaDxtTcCy
A::GROUP@:tcy
A::EVERYONE@:{rx}tcy
A:fdi:OWNER@:rwaDxtTcCy
A:fdi:GROUP@:tcy
A:fdi:EVERYONE@:tcy
        """
            fn_acl = '/tmp/acl.dat'
            open(fn_acl, 'w').write(acl)
            bash(f'nfs4_setfacl -S {fn_acl} {path}')
        else:
            NotImplementedError(f'_mkdir acl_backend {acl_backend}')
        logger.info(f"+ created dir: {path}")
    return not existed


def _rmdir(path):
    """
    @summary: remove a directory recursively
    @param path: the directory to remove
    @type path: str
    """
    if not os.path.exists(path):
        logger.warning(f"! cannot remove dir: {path}, it does not exist")
        return
    assert os.path.isdir(path), f"{path} is present but not a directory"
    dir_util.remove_tree(path)
    logger.info(f"- removed dir: {path}")


def _grantaccess(user, folder, readonly = False, recursive = False, follow = False):
    R = '-R' if recursive else ''
    uid = user.profile.userid
    if acl_backend == 'nfs4':
        acl = 'rXtcy' if readonly else 'rwaDxtcy'
        flags = 'fdi' if follow else ''
        bash(f'nfs4_setfacl {R} -a A:{flags}:{uid}:{acl} {folder}')
    elif acl_backend == 'posix':
        acl = 'rX' if readonly else 'rwx'
        bash(f'setfacl {R} -m u:{uid}:{acl} {folder}')
    else:
        NotImplementedError(f'_grantaccess acl_backend {acl_backend}')
    logger.info(f"+ access granted on dir {folder} to user {user}")


def _revokeaccess(user, folder):
    if acl_backend == 'nfs4':
        bash(f'nfs4_setfacl -R -x A:fdi:{user.profile.userid}:$(nfs4_getfacl {folder} | grep :fdi:{user.profile.userid}: | sed s,.*:,,) {folder}')
        bash(f'nfs4_setfacl -R -x A::{user.profile.userid}:$(nfs4_getfacl {folder} | grep ::{user.profile.userid}: | sed s,.*:,,) {folder}')
    elif acl_backend == 'posix':
        bash("setfacl -R -x u:%d %s" % (user.profile.userid, folder))
    else:
        NotImplementedError(f'_grantaccess acl_backend {acl_backend}')
    logger.info(f"- access revoked on dir {folder} from user {user}")


def _grantgroupaccess(group, folder, readonly = False, recursive = False, follow = False):
    R = '-R' if recursive else ''
    if isinstance(group, int):
        gid = group
    else:
        gid = group.groupid
    if acl_backend == 'nfs4':
        acl = 'rXtcy' if readonly else 'rwaDxtcy'
        flags = 'fdig' if follow else 'g'
        bash(f'nfs4_setfacl {R} -a A:{flags}:{gid}:{acl} {folder}')
    else:
        NotImplementedError(f'_grantaccess acl_backend {acl_backend}')
    logger.info(f"+ access granted on dir {folder} to group {gid}")

def _revokegroupaccess(group, folder):
    if acl_backend == 'nfs4':
        # FIXME csak group.id nem lesz jo, vagy eleve azt adjuk at
        bash(f'nfs4_setfacl -R -x A:fdig:{group_id}:$(nfs4_getfacl {folder} | grep :fdig:{group_id}: | sed s,.*:,,) {folder}')
        bash(f'nfs4_setfacl -R -x A:g:{group.groupid}:$(nfs4_getfacl {folder} | grep :g:{group.groupid}: | sed s,.*:,,) {folder}')
    else:
        NotImplementedError(f'_grantaccess acl_backend {acl_backend}')
    #logger.info(f"- access revoked on dir {folder} from group {group.groupid}")
    logger.info(f"- access revoked on dir {folder} from group {groupid}")


def _makeroot(ti):
    ti.uid = 0
    ti.gid = 0
    ti.uname = 'root'
    ti.gname = 'root'
    return ti

def _archivedir(folder, target, remove = True, fakeroot = True):
    if not os.path.exists(folder):
        logger.warning("Folder %s is missing" % folder)
        return
    try:
        assert len(os.listdir(folder)) > 0, "Folder %s is empty" % folder
        dir_util.mkpath(os.path.dirname(target))
        with tarfile.open(target, mode='w:gz') as archive:
            if fakeroot:
                archive.add(folder, arcname = '.', recursive = True, filter = _makeroot)
            else:
                archive.add(folder, arcname = '.', recursive = True)
            logger.debug("tar %s -> %s" % (folder, target))
    except Exception as e:
        logger.error(f"Cannot create archive {target} -- {e}")
    finally:
        if remove:
            _rmdir(folder)


def _extracttarbal(tarbal, target):
    if os.path.exists(target):
        logger.warning(f"Extract target folder {target} exists, may overwrite content")
    try:
        with tarfile.open(tarbal, mode = 'r') as archive:
            archive.extractall(path = target)
        logger.info(f"Extracted archive {tarbal} to folder {target}")
    except Exception as e:
        logger.error(f"Cannot extract archive {tarbal} to folder {target} -- {e}")


def _chown(path, uid = hub_uid, gid = hub_gid):
    for root, dirs, files in os.walk(path):
        for momo in dirs:
          os.chown(os.path.join(root, momo), uid, gid)
        for momo in files:
          os.chown(os.path.join(root, momo), uid, gid)


def _copy_dir(f_source, f_target, remove = False):
    if not os.path.exists(f_source):
        msg = "Folder %s not found" % f_source
        logger.error(msg)
        raise Exception(msg)
    dir_util.copy_tree(f_source, f_target)
    logger.info("copied %s -> %s" % (f_source, f_target))
    if remove:
        _rmdir(f_source)


###FIXME: #FIXME:
###FIXME: #@sudo
###FIXME: #def _createfile(fn, content, uid = 0, gid = 0, mode = 0b111101000):
###FIXME: #    with open(fn, 'w') as f:
###FIXME: #        f.write(content)
###FIXME: #    os.chown(fn, uid, gid)
###FIXME: #    os.chmod(fn, mode)
###FIXME: #    logger.info("Created file: %s" % fn)
###FIXME: 
###FIXME: ########################################
###FIXME: 
###FIXME: 


###FIXME: #@sudo
###FIXME: #def _dir_walker(root):
###FIXME: #    records = []
###FIXME: #    for path, dirs, files in os.walk(root):
###FIXME: #        for folder in dirs:
###FIXME: #            d = os.path.join(path, folder)
###FIXME: #            o = os.stat(d)
###FIXME: #            records.append((d, o.st_uid, o.st_gid))
###FIXME: #    logger.debug(f'treewalk: {records}')
###FIXME: #    return records


