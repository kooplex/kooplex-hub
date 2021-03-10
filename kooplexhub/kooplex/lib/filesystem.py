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

from kooplex.lib import bash, Dirname, Filename, sudo, now
from kooplex import settings as kooplex_settings

logger = logging.getLogger(__name__)

#FIXME: users group (1000) hardcoded and adde extra (should be removed when acl handling is resolved)
@sudo
def _mkdir(path, other_rx = False):
    """
    @summary: make a directory
    @param path: the directory to make
    @type path: str
    """
    dir_util.mkpath(path)
    assert os.path.exists(path), f"{path} is not present in the filesystem"
    assert os.path.isdir(path), f"{path} is present but not a directory"
    rx = 'rx' if other_rx else ''
    acl = f"""
A::OWNER@:rwaDxtTcCy
A::{kooplex_settings.HUB.pw_uid}:rwaDxtcy
A::GROUP@:tcy
A:g:{kooplex_settings.HUB.pw_gid}:rwaDxtcy
A:g:1000:rwaDxtcy
A::EVERYONE@:{rx}tcy
A:fdi:OWNER@:rwaDxtTcCy
A:fdi:GROUP@:tcy
A:fdig:{kooplex_settings.HUB.pw_gid}:rwaDxtcy
A:fdig:1000:rwaDxtcy
A:fdi:EVERYONE@:tcy
    """
    fn_acl = '/tmp/acl.dat'
    open(fn_acl, 'w').write(acl)
    bash(f'nfs4_setfacl -S {fn_acl} {path}')
    logger.info(f"+ created dir: {path}")

@sudo
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



#FIXME: posix/nfs
@sudo
def _grantaccess(user, folder, acl = 'rwaDxtcy'):
#    bash("setfacl -R -m u:%d:%s %s" % (user.profile.userid, acl, folder))
    bash(f'nfs4_setfacl -R -a A::{user.profile.userid}:{acl} {folder}')
    bash(f'nfs4_setfacl -R -a A:fdi:{user.profile.userid}:{acl} {folder}')
    logger.info(f"+ access granted on dir {folder} to user {user}")

@sudo
def _revokeaccess(user, folder):
#    bash("setfacl -R -x u:%d %s" % (user.profile.userid, folder))
    bash(f'nfs4_setfacl -R -x A:fdi:{user.profile.userid}:$(nfs4_getfacl {folder} | grep :fdi:{user.profile.userid}: | sed s,.*:,,) {folder}')
    bash(f'nfs4_setfacl -R -x A::{user.profile.userid}:$(nfs4_getfacl {folder} | grep ::{user.profile.userid}: | sed s,.*:,,) {folder}')
    logger.info(f"- access revoked on dir {folder} from user {user}")

@sudo
def _grantgroupaccess(group_id, folder, acl = 'rxtcy'):
    bash(f'nfs4_setfacl -R -a A:g:{group_id}:{acl} {folder}')
    bash(f'nfs4_setfacl -R -a A:fdig:{group_id}:{acl} {folder}')
    #bash(f'nfs4_setfacl -R -a A:fdig:{groupi_id}:{acl} {folder}')
    logger.info(f"+ access granted on dir {folder} to group {group_id}")

@sudo
def _revokegroupaccess(group_id, folder):
    #bash(f'nfs4_setfacl -R -x A:fdig:{group_id}:$(nfs4_getfacl {folder} | grep :fdig:{group_id}: | sed s,.*:,,) {folder}')
    bash(f'nfs4_setfacl -R -x A:g:{group_id}:$(nfs4_getfacl {folder} | grep :g:{group_id}: | sed s,.*:,,) {folder}')
    logger.info(f"- access revoked on dir {folder} from group {group_id}")

@sudo
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


@sudo
def _copy_dir(f_source, f_target, remove = False):
    if not os.path.exists(f_source):
        msg = "Folder %s not found" % f_source
        logger.error(msg)
        raise Exception(msg)
    dir_util.copy_tree(f_source, f_target)
    logger.info("copied %s -> %s" % (f_source, f_target))
    if remove:
        _rmdir(f_source)


#FIXME:
#@sudo
#def _createfile(fn, content, uid = 0, gid = 0, mode = 0b111101000):
#    with open(fn, 'w') as f:
#        f.write(content)
#    os.chown(fn, uid, gid)
#    os.chmod(fn, mode)
#    logger.info("Created file: %s" % fn)

########################################


def check_home(user): #FIXME: add to _mkdir silent no exception 2 raise
    dir_home = Dirname.userhome(user)
    assert os.path.exists(dir_home), "Folder %s does not exist" % dir_home
#TODO: check permissions


########################################
# user folder management

def mkdir_home(user):
    """
    @summary: create a home directory and garbage folder for the user
    @param user: the user
    @type user: kooplex.hub.models.User
    """
    dir_home = Dirname.userhome(user)
    _mkdir(dir_home)
    _grantaccess(user, dir_home)
    dir_usergarbage = Dirname.usergarbage(user)
    _mkdir(dir_usergarbage)
    _grantaccess(user, dir_usergarbage)

def garbagedir_home(user):
    dir_home = Dirname.userhome(user)
    garbage = Filename.userhome_garbage(user)
    _archivedir(dir_home, garbage)
    dir_usergarbage = Dirname.usergarbage(user)
    if not os.path.exists(dir_usergarbage):
        logger.warning(f'! usergarbage dir {dir_usergarbage} does not exist')
        return
    if not os.listdir(dir_usergarbage):
        logger.info(f'- usergarbage dir {dir_usergarbage} is empty, removed')
    else:
        d_new = f'{dir_usergarbage}-{now()}'
        os.rename(dir_usergarbage, d_new)
        logger.info(f'+ usergarbage dir {dir_usergarbage} rename {d_new}')


########################################
# project folder management

def mkdir_project(project):
    dir_project = Dirname.project(project)
    _mkdir(dir_project)
    _grantaccess(project.creator, dir_project)
    _grantgroupaccess(project.groupid, dir_project, acl = 'rwaDxtcy')
    dir_reportprepare = Dirname.reportprepare(project)
    _mkdir(dir_reportprepare)
    _grantaccess(project.creator, dir_reportprepare)
    _grantgroupaccess(project.groupid, dir_reportprepare, acl = 'rwaDxtcy')

#@sudo
#def _dir_walker(root):
#    records = []
#    for path, dirs, files in os.walk(root):
#        for folder in dirs:
#            d = os.path.join(path, folder)
#            o = os.stat(d)
#            records.append((d, o.st_uid, o.st_gid))
#    logger.debug(f'treewalk: {records}')
#    return records

def grantaccess_project(userprojectbinding):
    user = userprojectbinding.user
    dir_project = Dirname.project(userprojectbinding.project)
    _grantaccess(user, dir_project)
#    for subdir, uid, gid in _dir_walker(dir_project):
#        _grantaccess(user, subdir, uid = uid, gid = gid)
    dir_reportprepare = Dirname.reportprepare(userprojectbinding.project)
    _grantaccess(user, dir_reportprepare)
#    for subdir, uid, gid in _dir_walker(dir_reportprepare):
#        _grantaccess(user, subdir, uid = uid, gid = gid)

def revokeaccess_project(userprojectbinding):
    user = userprojectbinding.user
    dir_project = Dirname.project(userprojectbinding.project)
#    for subdir, uid, gid in _dir_walker(dir_project):
#        _revokeaccess(user, subdir, uid = uid, gid = gid)
    _revokeaccess(user, dir_project)
    dir_reportprepare = Dirname.reportprepare(userprojectbinding.project)
#    for subdir, uid, gid in _dir_walker(dir_reportprepare):
#        _revokeaccess(user, subdir, uid = uid, gid = gid)
    _revokeaccess(user, dir_reportprepare)

def garbagedir_project(project):
    dir_project = Dirname.project(project)
    garbage = Filename.project_garbage(project)
    _archivedir(dir_project, garbage)
    dir_reportprepare = Dirname.reportprepare(project)
    _rmdir(dir_reportprepare)


########################################
# report folder management

def check_reportprepare(user):
    dir_reportprepare = Dirname.reportprepare(user)
    assert os.path.exists(dir_reportprepare), "Folder %s does not exist" % dir_reportprepare

@sudo
def snapshot_report(report):
    project_report_root = Dirname.reportroot(report.project)
    if not os.path.exists(project_report_root):
        _mkdir(project_report_root, other_rx = True)
        n = report.mark_projectservices_restart(f"Need to mount report folder for project {report.project}")
        logger.info(f'{n} services marked as need to restart, due to creation of folder {project_report_root}')
    dir_source = os.path.join(Dirname.reportprepare(report.project), report.folder)
    dir_target = Dirname.report(report)
    _copy_dir(dir_source, dir_target, remove = False)
    _grantgroupaccess(1000, dir_target) #FIXME hardcoded, ez szerintem nem is kell!!!
    _grantgroupaccess(report.project.groupid, dir_target)
    #TODO _grantaccess report reader if different than hub

#FIXME: ha muxik a group majd nem kell
@sudo
def grantaccess_report(report, user):
    dir_report = Dirname.report(report)
    #_grantaccess(user, dir_report)

@sudo
def revokeaccess_report(report, user):
    dir_report = Dirname.report(report)
    #_revokeaccess(user, dir_report)

@sudo
def garbage_report(report):
    dir_source = Dirname.report(report)
    garbage = Filename.report_garbage(report)
    _archivedir(dir_source, garbage, remove = True)
    project_report_root = Dirname.reportroot(report.project)
    if not os.path.exists(project_report_root):
        logger.warning(f'! folder {project_report_root} missing...')
        return
    if len(os.listdir(project_report_root)) == 0:
        os.rmdir(project_report_root)
        logger.info(f'- removed empty folder {project_report_root}')
        n = report.mark_projectservices_restart(f"need to umount emptied report folder for project {report.project}")
        logger.info(f'{n} services marked as need to restart, due to removal of folder {project_report_root}')

@sudo
def recreate_report(report):
    dir_source = os.path.join(Dirname.reportprepare(report.project), report.folder)
    assert os.path.exists(dir_source), f"Report folder {dir_source} does not exist."
    index_source = os.path.join(Dirname.reportprepare(report.project), report.folder, report.index)
    assert os.path.exists(index_source), f"Report index {index_source} in folder {dir_source} does not exist."
    dir_target = Dirname.report(report)
    _rmdir(dir_target)
    snapshot_report(report)


########################################
# attachment folder management

@sudo
def mkdir_attachment(attachment):
    dir_attachment = Dirname.attachment(attachment)
    _mkdir(dir_attachment, other_rx = True)
    _grantaccess(attachment.creator, dir_attachment)

@sudo
def garbage_attachment(attachment):
    dir_attachment = Dirname.attachment(attachment)
    garbage = Filename.attachment_garbage(attachment)
    _archivedir(dir_attachment, garbage, remove = True)



########################################


#################################################################################

#FIXME:
def mkdir_course_share(course):
    try:
        dir_courseprivate = Dirname.courseprivate(course)
        _mkdir(dir_courseprivate, gid = course.groupid, mode = 0o770)
        dir_coursepublic = Dirname.coursepublic(course)
        _mkdir(dir_coursepublic, gid = course.groupid, mode = 0o750)
        logger.info("Course dir created for course %s" % course)
    except KeyError as e:
        logger.error("Cannot create course dir, KOOPLEX['mountpoint']['course'] is missing")


def grantacl_course_share(usercoursebinding):
    try:
        dir_coursepublic = Dirname.coursepublic(usercoursebinding.course)
        dir_courseprivate = Dirname.courseprivate(usercoursebinding.course)
        if usercoursebinding.is_teacher:
            _grantaccess(usercoursebinding.user, dir_coursepublic)
            _grantaccess(usercoursebinding.user, dir_courseprivate)
        else:
            _grantaccess(usercoursebinding.user, dir_coursepublic, acl = 'rX')
    except Exception as e:
        logger.error("Cannot grant acl %s -- %s" % (usercoursebinding, e))

def revokeacl_course_share(usercoursebinding):
    try:
        dir_coursepublic = Dirname.coursepublic(usercoursebinding.course)
        dir_courseprivate = Dirname.courseprivate(usercoursebinding.course)
        if usercoursebinding.is_teacher:
            _revokeaccess(usercoursebinding.user, dir_courseprivate)
        _revokeaccess(usercoursebinding.user, dir_coursepublic)
    except Exception as e:
        logger.error("Cannot revoke acl %s -- %s" % (usercoursebinding, e))


def garbagedir_course_share(course):
    dir_course = Dirname.course(course)
    garbage = Filename.course_garbage(course)
    _archivedir(dir_course, garbage)


def mkdir_course_workdir(usercoursebinding):
    try:
        dir_usercourse = Dirname.usercourseworkdir(usercoursebinding)
        uid = usercoursebinding.user.profile.userid
        gid = usercoursebinding.course.groupid
        _mkdir(dir_usercourse, uid = uid, gid = gid, mode = 0o770)
    except KeyError as e:
        logger.error("Cannot create course dir, KOOPLEX['mountpoint']['usercourse'] is missing")


def grantacl_course_workdir(usercoursebinding):
    try:
        if usercoursebinding.is_teacher:
            dir_usercourse = Dirname.courseworkdir(usercoursebinding)
            _grantaccess(usercoursebinding.user, dir_usercourse, acl = 'rX') #NOTE: formerly rw access was granted
    except Exception as e:
        logger.error("Cannot grant acl %s -- %s" % (usercoursebinding, e))

def revokeacl_course_workdir(usercoursebinding):
    try:
        if usercoursebinding.is_teacher:
            dir_usercourse = Dirname.courseworkdir(usercoursebinding)
            _revokeaccess(usercoursebinding.user, dir_usercourse)
    except Exception as e:
        logger.error("Cannot revoke acl %s -- %s" % (usercoursebinding, e))


def archive_course_workdir(usercoursebinding):
    if usercoursebinding.is_teacher:
        return
    dir_usercourse = Dirname.usercourseworkdir(usercoursebinding)
    archive = Filename.courseworkdir_archive(usercoursebinding)
    _archivedir(dir_usercourse, archive)


def rmdir_course_workdir(course):
    try:
        dir_usercourse = Dirname.course(course)
        dir_util.remove_tree(dir_usercourse)
    except KeyError as e:
        logger.error("Cannot remove course dir, KOOPLEX['mountpoint']['usercourse'] is missing")
    except Exception as e:
        logger.error("Cannot remove course %s workdir -- %s" % (course, e))

def snapshot_assignment(assignment):
    dir_source = Dirname.assignmentsource(assignment)
    archive = Filename.assignmentsnapshot(assignment)
    _archivedir(dir_source, archive, remove = False)

def garbage_assignmentsnapshot(assignment):
    try:
        archive = Filename.assignmentsnapshot(assignment)
        garbage = Filename.assignmentsnapshot_garbage(assignment)
        file_util.move_file(archive, garbage)
    except Exception as e:
        logger.error("move %s -> %s fails -- %s" % (archive, garbage, e))

def cp_assignmentsnapshot(userassignmentbinding):
    from hub.models import UserCourseBinding
    try:
        assignment = userassignmentbinding.assignment
        archivefile = Filename.assignmentsnapshot(assignment)
        dir_target = Dirname.assignmentworkdir(userassignmentbinding)
        with tarfile.open(archivefile, mode = 'r') as archive:
            archive.extractall(path = dir_target)
        _revokeaccess(userassignmentbinding.user, dir_target)
        for binding in UserCourseBinding.objects.filter(course = assignment.coursecode.course, is_teacher = True):
            _grantaccess(binding.user, dir_target, acl = 'rX')
    except Exception as e:
        logger.error("Cannot cp snapshot dir %s -- %s" % (userassignmentbinding, e))

def cp_userassignment(userassignmentbinding):
    dir_source = Dirname.assignmentworkdir(userassignmentbinding)
    archive = Filename.assignmentcollection(userassignmentbinding)
    _archivedir(dir_source, archive, remove = userassignmentbinding.assignment.remove_collected)

def cp_userassignment2correct(userassignmentbinding):
    try:
        archivefile = Filename.assignmentcollection(userassignmentbinding)
        dir_target = Dirname.assignmentcorrectdir(userassignmentbinding)
        with tarfile.open(archivefile, mode='r') as archive:
            archive.extractall(path = dir_target)
        _grantaccess(userassignmentbinding.corrector, dir_target, acl = 'rwX')
        _grantaccess(userassignmentbinding.user, dir_target, acl = 'rX')
    except Exception as e:
        logger.error("Cannot copy correct dir %s -- %s" % (userassignmentbinding, e))

