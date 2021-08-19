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
from distutils import dir_util
from distutils import file_util
import tarfile

from ..lib import dirname, filename, bash

try:
    from kooplexhub.settings import KOOPLEX
except ImportError:
    logger.warning('Missing KOOPLEX configuration dictionary from settings.py')
    KOOPLEX = {}

logger = logging.getLogger(__name__)

acl_backend = KOOPLEX.get('fs_backend', 'nfs4')
hub_uid = KOOPLEX.get('hub_uid', 0)
hub_gid = KOOPLEX.get('hub_gid', 0)

assert acl_backend in [ 'nfs4', 'posix' ], "Only 'nfs4' and 'posix' acl_backends are supported"

#FIXME: @sudo
def _mkdir(path, other_rx = False):
    """
    @summary: make a directory
    @param path: the directory to make
    @type path: str
    """
    logger.info(f'acl_backend: {acl_backend}')
    existed = os.path.isdir(path)
    dir_util.mkpath(path)
    assert os.path.exists(path), f"{path} is not present in the filesystem"
    assert os.path.isdir(path), f"{path} is present but not a directory"
    rx = 'rx' if other_rx else ''
    if acl_backend == 'nfs4':
        acl = f"""
A::OWNER@:rwaDxtTcCy
A::{hub_uid}:rwaDxtcy
A::GROUP@:tcy
A:g:{hub_gid}:rwaDxtcy
A::EVERYONE@:{rx}tcy
A:fdi:OWNER@:rwaDxtTcCy
A:fdi:GROUP@:tcy
A:fdig:{hub_gid}:rwaDxtcy
A:fdi:EVERYONE@:tcy
    """
        fn_acl = '/tmp/acl.dat'
        open(fn_acl, 'w').write(acl)
        bash(f'nfs4_setfacl -S {fn_acl} {path}')
    else:
        NotImplementedError(f'_mkdir acl_backend {acl_backend}')
    if not existed:
        logger.info(f"+ created dir: {path}")


##FIXME: @sudo
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


##@sudo
def _grantaccess(user, folder, acl = 'rwaDxtcy'):
    if acl_backend == 'nfs4':
        bash(f'nfs4_setfacl -R -a A::{user.profile.userid}:{acl} {folder}')
        bash(f'nfs4_setfacl -R -a A:fdi:{user.profile.userid}:{acl} {folder}')
    elif acl_backend == 'posix':
        acl = re.sub('[aDtcy]', '', acl)
        bash("setfacl -R -m u:%d:%s %s" % (user.profile.userid, acl, folder))
    else:
        NotImplementedError(f'_grantaccess acl_backend {acl_backend}')
    logger.info(f"+ access granted on dir {folder} to user {user}")


###FIXME: @sudo
def _revokeaccess(user, folder):
    if acl_backend == 'nfs4':
        bash(f'nfs4_setfacl -R -x A:fdi:{user.profile.userid}:$(nfs4_getfacl {folder} | grep :fdi:{user.profile.userid}: | sed s,.*:,,) {folder}')
        bash(f'nfs4_setfacl -R -x A::{user.profile.userid}:$(nfs4_getfacl {folder} | grep ::{user.profile.userid}: | sed s,.*:,,) {folder}')
    elif acl_backend == 'posix':
        bash("setfacl -R -x u:%d %s" % (user.profile.userid, folder))
    else:
        NotImplementedError(f'_grantaccess acl_backend {acl_backend}')
    logger.info(f"- access revoked on dir {folder} from user {user}")


###FIXME: @sudo
def _grantgroupaccess(group_id, folder, acl = 'rxtcy'):
    if acl_backend == 'nfs4':
        bash(f'nfs4_setfacl -R -a A:g:{group_id}:{acl} {folder}')
        bash(f'nfs4_setfacl -R -a A:fdig:{group_id}:{acl} {folder}')
        #bash(f'nfs4_setfacl -R -a A:fdig:{groupi_id}:{acl} {folder}')
    else:
        NotImplementedError(f'_grantaccess acl_backend {acl_backend}')
    logger.info(f"+ access granted on dir {folder} to group {group_id}")


###FIXME: @sudo
def _revokegroupaccess(group_id, folder):
    if acl_backend == 'nfs4':
        #bash(f'nfs4_setfacl -R -x A:fdig:{group_id}:$(nfs4_getfacl {folder} | grep :fdig:{group_id}: | sed s,.*:,,) {folder}')
        bash(f'nfs4_setfacl -R -x A:g:{group_id}:$(nfs4_getfacl {folder} | grep :g:{group_id}: | sed s,.*:,,) {folder}')
    else:
        NotImplementedError(f'_grantaccess acl_backend {acl_backend}')
    logger.info(f"- access revoked on dir {folder} from group {group_id}")


###FIXME: @sudo
def _archivedir(folder, target, remove = True):
    if not os.path.exists(folder):
        logger.warning("Folder %s is missing" % folder)
        return
    try:
        assert len(os.listdir(folder)) > 0, "Folder %s is empty" % folder
        dir_util.mkpath(os.path.dirname(target))
        with tarfile.open(target, mode='w:gz') as archive:
            archive.add(folder, arcname = '.', recursive = True)
            logger.debug("tar %s -> %s" % (folder, target))
    except Exception as e:
        logger.error(f"Cannot create archive {target} -- {e}")
    finally:
        if remove:
            _rmdir(folder)


###FIXME: @sudo
###FIXME: def _copy_dir(f_source, f_target, remove = False):
###FIXME:     if not os.path.exists(f_source):
###FIXME:         msg = "Folder %s not found" % f_source
###FIXME:         logger.error(msg)
###FIXME:         raise Exception(msg)
###FIXME:     dir_util.copy_tree(f_source, f_target)
###FIXME:     logger.info("copied %s -> %s" % (f_source, f_target))
###FIXME:     if remove:
###FIXME:         _rmdir(f_source)
###FIXME: 
###FIXME: 
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

########################################
# user folder management

def mkdir_home(user):
    """
    @summary: create a home directory and garbage folder for the user
    @param user: the user
    @type user: kooplex.hub.models.User
    """
    dir_home = dirname.userhome(user)
    _mkdir(dir_home)
    _grantaccess(user, dir_home)
    dir_usergarbage = dirname.usergarbage(user)
    _mkdir(dir_usergarbage)
    _grantaccess(user, dir_usergarbage)

###FIXME: def garbagedir_home(user):
###FIXME:     dir_home = Dirname.userhome(user)
###FIXME:     garbage = Filename.userhome_garbage(user)
###FIXME:     _archivedir(dir_home, garbage)
###FIXME:     dir_usergarbage = Dirname.usergarbage(user)
###FIXME:     if not os.path.exists(dir_usergarbage):
###FIXME:         logger.warning(f'! usergarbage dir {dir_usergarbage} does not exist')
###FIXME:         return
###FIXME:     if not os.listdir(dir_usergarbage):
###FIXME:         logger.info(f'- usergarbage dir {dir_usergarbage} is empty, removed')
###FIXME:     else:
###FIXME:         d_new = f'{dir_usergarbage}-{now()}'
###FIXME:         os.rename(dir_usergarbage, d_new)
###FIXME:         logger.info(f'+ usergarbage dir {dir_usergarbage} rename {d_new}')


########################################
# project folder management

def mkdir_project(project):
    dir_project = dirname.project(project)
    _mkdir(dir_project)
    _grantaccess(project.creator, dir_project)
    _grantgroupaccess(project.groupid, dir_project, acl = 'rwaDxtcy')
    dir_reportprepare = dirname.report_prepare(project)
    _mkdir(dir_reportprepare)
    _grantaccess(project.creator, dir_reportprepare)
    _grantgroupaccess(project.groupid, dir_reportprepare, acl = 'rwaDxtcy')

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


def grantaccess_project(userprojectbinding):
    user = userprojectbinding.user
    dir_project = dirname.project(userprojectbinding.project)
    _grantaccess(user, dir_project)
#    for subdir, uid, gid in _dir_walker(dir_project):
#        _grantaccess(user, subdir, uid = uid, gid = gid)
    dir_reportprepare = dirname.report_prepare(userprojectbinding.project)
    _grantaccess(user, dir_reportprepare)
#    for subdir, uid, gid in _dir_walker(dir_reportprepare):
#        _grantaccess(user, subdir, uid = uid, gid = gid)


def revokeaccess_project(userprojectbinding):
    user = userprojectbinding.user
    dir_project = dirname.project(userprojectbinding.project)
#    for subdir, uid, gid in _dir_walker(dir_project):
#        _revokeaccess(user, subdir, uid = uid, gid = gid)
    _revokeaccess(user, dir_project)
    dir_reportprepare = dirname.report_prepare(userprojectbinding.project)
#    for subdir, uid, gid in _dir_walker(dir_reportprepare):
#        _revokeaccess(user, subdir, uid = uid, gid = gid)
    _revokeaccess(user, dir_reportprepare)


def garbagedir_project(project):
    dir_project = dirname.project(project)
    garbage = filename.project_garbage(project)
    _archivedir(dir_project, garbage)
    dir_reportprepare = dirname.report_prepare(project)
    _rmdir(dir_reportprepare)


###FIXME: ########################################
###FIXME: # report folder management
###FIXME: 
###FIXME: def check_reportprepare(user):
###FIXME:     dir_reportprepare = Dirname.reportprepare(user)
###FIXME:     assert os.path.exists(dir_reportprepare), "Folder %s does not exist" % dir_reportprepare
###FIXME: 
###FIXME: @sudo
###FIXME: def snapshot_report(report):
###FIXME:     project_report_root = Dirname.reportroot(report.project)
###FIXME:     if not os.path.exists(project_report_root):
###FIXME:         _mkdir(project_report_root, other_rx = True)
###FIXME:         n = report.mark_projectservices_restart(f"Need to mount report folder for project {report.project}")
###FIXME:         logger.info(f'{n} services marked as need to restart, due to creation of folder {project_report_root}')
###FIXME:     dir_source = os.path.join(Dirname.reportprepare(report.project), report.folder)
###FIXME:     dir_target = Dirname.report(report)
###FIXME:     _copy_dir(dir_source, dir_target, remove = False)
###FIXME:     _grantgroupaccess(1000, dir_target) #FIXME hardcoded, ez szerintem nem is kell!!!
###FIXME:     _grantgroupaccess(report.project.groupid, dir_target)
###FIXME:     #TODO _grantaccess report reader if different than hub
###FIXME: 
###FIXME: #FIXME: ha muxik a group majd nem kell
###FIXME: @sudo
###FIXME: def grantaccess_report(report, user):
###FIXME:     dir_report = Dirname.report(report)
###FIXME:     #_grantaccess(user, dir_report)
###FIXME: 
###FIXME: @sudo
###FIXME: def revokeaccess_report(report, user):
###FIXME:     dir_report = Dirname.report(report)
###FIXME:     #_revokeaccess(user, dir_report)
###FIXME: 
###FIXME: @sudo
###FIXME: def garbage_report(report):
###FIXME:     dir_source = Dirname.report(report)
###FIXME:     garbage = Filename.report_garbage(report)
###FIXME:     _archivedir(dir_source, garbage, remove = True)
###FIXME:     project_report_root = Dirname.reportroot(report.project)
###FIXME:     if not os.path.exists(project_report_root):
###FIXME:         logger.warning(f'! folder {project_report_root} missing...')
###FIXME:         return
###FIXME:     if len(os.listdir(project_report_root)) == 0:
###FIXME:         os.rmdir(project_report_root)
###FIXME:         logger.info(f'- removed empty folder {project_report_root}')
###FIXME:         n = report.mark_projectservices_restart(f"need to umount emptied report folder for project {report.project}")
###FIXME:         logger.info(f'{n} services marked as need to restart, due to removal of folder {project_report_root}')
###FIXME: 
###FIXME: @sudo
###FIXME: def recreate_report(report):
###FIXME:     dir_source = os.path.join(Dirname.reportprepare(report.project), report.folder)
###FIXME:     assert os.path.exists(dir_source), f"Report folder {dir_source} does not exist."
###FIXME:     index_source = os.path.join(Dirname.reportprepare(report.project), report.folder, report.index)
###FIXME:     assert os.path.exists(index_source), f"Report index {index_source} in folder {dir_source} does not exist."
###FIXME:     dir_target = Dirname.report(report)
###FIXME:     _rmdir(dir_target)
###FIXME:     snapshot_report(report)
###FIXME: 
###FIXME: 
###FIXME: ########################################
###FIXME: # attachment folder management
###FIXME: 
###FIXME: @sudo
###FIXME: def mkdir_attachment(attachment):
###FIXME:     dir_attachment = Dirname.attachment(attachment)
###FIXME:     _mkdir(dir_attachment, other_rx = True)
###FIXME:     _grantaccess(attachment.creator, dir_attachment)
###FIXME: 
###FIXME: @sudo
###FIXME: def garbage_attachment(attachment):
###FIXME:     dir_attachment = Dirname.attachment(attachment)
###FIXME:     garbage = Filename.attachment_garbage(attachment)
###FIXME:     _archivedir(dir_attachment, garbage, remove = True)
###FIXME: 
###FIXME: 
###FIXME: 
###FIXME: ########################################
###FIXME: 
###FIXME: 
###FIXME: #################################################################################

def mkdir_course(course):
    '''
@summary creates course related folders:
    `mount_pointhub:course`/`course.folder`/public
    `mount_pointhub:course`/`course.folder`/assignment_prepare
    `mount_pointhub:course`/`course.folder`/assignment_snapshot
    `mount_pointhub:course_workdir`/`course.folder`/
    `mount_pointhub:course_assignment`/`course.folder`/
    '''
    logger.debug(f"mkdir_course for course {course.name}")
    dir_coursepublic = dirname.course_public(course)
    _mkdir(dir_coursepublic)
    dir_assignmentprepare = dirname.course_assignment_prepare_root(course)
    _mkdir(dir_assignmentprepare)
    dir_assignmentsnapshot = dirname.course_assignment_snapshot(course)
    _mkdir(dir_assignmentsnapshot)
    dir_workdir = dirname.course_workdir_root(course)
    _mkdir(dir_workdir)
    dir_assignment = dirname.course_assignment_root(course)
    _mkdir(dir_assignment)
    #FIXME: grantaccess


###FIXME: def grantacl_course_share(usercoursebinding):
###FIXME:     try:
###FIXME:         dir_coursepublic = Dirname.coursepublic(usercoursebinding.course)
###FIXME:         dir_courseprivate = Dirname.courseprivate(usercoursebinding.course)
###FIXME:         if usercoursebinding.is_teacher:
###FIXME:             _grantaccess(usercoursebinding.user, dir_coursepublic)
###FIXME:             _grantaccess(usercoursebinding.user, dir_courseprivate)
###FIXME:         else:
###FIXME:             _grantaccess(usercoursebinding.user, dir_coursepublic, acl = 'rX')
###FIXME:     except Exception as e:
###FIXME:         logger.error("Cannot grant acl %s -- %s" % (usercoursebinding, e))
###FIXME: 
###FIXME: def revokeacl_course_share(usercoursebinding):
###FIXME:     try:
###FIXME:         dir_coursepublic = Dirname.coursepublic(usercoursebinding.course)
###FIXME:         dir_courseprivate = Dirname.courseprivate(usercoursebinding.course)
###FIXME:         if usercoursebinding.is_teacher:
###FIXME:             _revokeaccess(usercoursebinding.user, dir_courseprivate)
###FIXME:         _revokeaccess(usercoursebinding.user, dir_coursepublic)
###FIXME:     except Exception as e:
###FIXME:         logger.error("Cannot revoke acl %s -- %s" % (usercoursebinding, e))
###FIXME: 
###FIXME: 
###FIXME: def garbagedir_course_share(course):
###FIXME:     dir_course = Dirname.course(course)
###FIXME:     garbage = Filename.course_garbage(course)
###FIXME:     _archivedir(dir_course, garbage)


def get_assignment_prepare_subfolders(course):
    dir_assignmentprepare = dirname.course_assignment_prepare_root(course)
    abs_path = lambda x: os.path.join(dir_assignmentprepare, x)
    not_empty_folder = lambda x: os.path.isdir(abs_path(x)) and len(os.listdir(abs_path(x))) > 0
    return list(filter(not_empty_folder, os.listdir(dir_assignmentprepare)))


def mkdir_course_workdir(usercoursebinding):
    '''
@summary creates course related subfolders for the user:
    `mount_pointhub:course_workdir`/`course.folder`/`user.username`
    for students:
    `mount_pointhub:course_assignment`/`course.folder`/`user.username`
    '''
    dir_workdir = dirname.course_workdir(usercoursebinding)
    _mkdir(dir_workdir)
    if not usercoursebinding.is_teacher:
        dir_assignment_workdir = dirname.assignment_workdir_root(usercoursebinding)
        _mkdir(dir_assignment_workdir)
    #FIXME: grantaccess


###FIXME: def grantacl_course_workdir(usercoursebinding):
###FIXME:     try:
###FIXME:         if usercoursebinding.is_teacher:
###FIXME:             dir_usercourse = Dirname.courseworkdir(usercoursebinding)
###FIXME:             _grantaccess(usercoursebinding.user, dir_usercourse, acl = 'rX') #NOTE: formerly rw access was granted
###FIXME:     except Exception as e:
###FIXME:         logger.error("Cannot grant acl %s -- %s" % (usercoursebinding, e))
###FIXME: 
###FIXME: def revokeacl_course_workdir(usercoursebinding):
###FIXME:     try:
###FIXME:         if usercoursebinding.is_teacher:
###FIXME:             dir_usercourse = Dirname.courseworkdir(usercoursebinding)
###FIXME:             _revokeaccess(usercoursebinding.user, dir_usercourse)
###FIXME:     except Exception as e:
###FIXME:         logger.error("Cannot revoke acl %s -- %s" % (usercoursebinding, e))


def delete_usercourse(usercoursebinding):
    #FIXME: garbage
    _rmdir(dirname.assignment_workdir_root(usercoursebinding))
    _rmdir(dirname.course_workdir(usercoursebinding))


def delete_course(course):
    #FIXME: garbage
    _rmdir(dirname.course_assignment_root(course))
    _rmdir(dirname.course_workdir_root(course))
    _rmdir(dirname.course_root(course))

###FIXME: def archive_course_workdir(usercoursebinding):
###FIXME:     if usercoursebinding.is_teacher:
###FIXME:         return
###FIXME:     dir_usercourse = Dirname.usercourseworkdir(usercoursebinding)
###FIXME:     archive = Filename.courseworkdir_archive(usercoursebinding)
###FIXME:     _archivedir(dir_usercourse, archive)


def snapshot_assignment(assignment):
    dir_source = dirname.assignment_source(assignment)
    archive = filename.assignment_snapshot(assignment)
    _archivedir(dir_source, archive, remove = False)

###FIXME: def garbage_assignmentsnapshot(assignment):
###FIXME:     try:
###FIXME:         archive = Filename.assignmentsnapshot(assignment)
###FIXME:         garbage = Filename.assignmentsnapshot_garbage(assignment)
###FIXME:         file_util.move_file(archive, garbage)
###FIXME:     except Exception as e:
###FIXME:         logger.error("move %s -> %s fails -- %s" % (archive, garbage, e))


def cp_assignmentsnapshot(userassignmentbinding):
    assignment = userassignmentbinding.assignment
    archivefile = filename.assignment_snapshot(assignment)
    dir_target = dirname.assignment_workdir(userassignmentbinding)
    with tarfile.open(archivefile, mode = 'r') as archive:
        archive.extractall(path = dir_target)
    logger.info(f"+ extracted {archivefile} in folder {dir_target}")
#FIXME        _revokeaccess(userassignmentbinding.user, dir_target)
#FIXME        for binding in UserCourseBinding.objects.filter(course = assignment.coursecode.course, is_teacher = True):
#FIXME            _grantaccess(binding.user, dir_target, acl = 'rX')


def snapshot_userassignment(userassignmentbinding):
    dir_source = dirname.assignment_workdir(userassignmentbinding)
    archive = filename.assignment_collection(userassignmentbinding)
    _archivedir(dir_source, archive, remove = userassignmentbinding.assignment.remove_collected)
    logger.info(f"+ created {archive} of folder {dir_source}")


def cp_userassignment2correct(userassignmentbinding):
    archivefile = filename.assignment_collection(userassignmentbinding)
    dir_target = dirname.assignment_correct_dir(userassignmentbinding)
    with tarfile.open(archivefile, mode='r') as archive:
        archive.extractall(path = dir_target)
    #FIXME: grant access
    #    _grantaccess(userassignmentbinding.corrector, dir_target, acl = 'rwX')
    #    _grantaccess(userassignmentbinding.user, dir_target, acl = 'rX')
    logger.info(f"+ extracted {archivefile} in folder {dir_target}")


def delete_userassignment(userassignmentbinding):
    #FIXME: garbage
    _rmdir(dirname.userassignment_dir(userassignmentbinding))
    _rmdir(dirname.assignment_correct_dir(userassignmentbinding))
    #FIXME: garbage/rm snapshots

