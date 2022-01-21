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

from ..lib import dirname, filename, bash
from hub.lib import background

try:
    from kooplexhub.settings import KOOPLEX
except ImportError:
    logger.warning('Missing KOOPLEX configuration dictionary from settings.py')
    KOOPLEX = {}

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



#FIXME: @sudo
def _mkdir(path, other_rx = False):
    """
    @summary: make a directory
    @param path: the directory to make
    @type path: str
    """
    logger.info(f'acl_backend: {acl_backend}')
    existed = os.path.isdir(path)
    if not existed:
        assert not os.path.exists(path), f"{path} is present in the filesystem, but not a directory"
        dir_util.mkpath(path)
        assert os.path.isdir(path), f"{path} directory not created"
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
@background
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
def _grantgroupaccess(group_id, folder, acl = 'rXtcy'):
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


def _chown(path, uid = hub_uid, gid = hub_gid):
    for root, dirs, files in os.walk(path):
        for momo in dirs:
          os.chown(os.path.join(root, momo), uid, gid)
        for momo in files:
          os.chown(os.path.join(root, momo), uid, gid)


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

def provision_home(user):
    """
    @summary: create a home directory and garbage folder for the user
    @param user: the user
    @type user: kooplex.hub.models.User
    """
    if user.is_superuser:
        logger.debug(f"user {user.username} is a superuser, skip creating home and garbage folders")
        return
    dir_home = dirname.userhome(user)
    created = _mkdir(dir_home)
    if created or KOOPLEX.get('fs_force_acl', False):
        _grantaccess(user, dir_home)
    dir_usergarbage = dirname.usergarbage(user)
    created = _mkdir(dir_usergarbage)
    if created or KOOPLEX.get('fs_force_acl', False):
        _grantaccess(user, dir_usergarbage)

def garbagedir_home(user):
    if user.is_superuser:
        logger.debug(f"user {user.username} is a superuser, skip garbage collection")
        return
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
# scratch folder management
def provision_scratch(user):
    """
    @summary: create a scratch directory for the user
    @param user: the user
    @type user: kooplex.hub.models.User
    """
    if user.is_superuser:
        logger.debug(f"user {user.username} is a superuser, skip creating scratch folder")
        return
    dir_scratch = dirname.userscratch(user)
    created = _mkdir(dir_scratch)
    if created or KOOPLEX.get('fs_force_acl', False):
        _grantaccess(user, dir_scratch)


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
    dir_reportprepare = dirname.report_prepare(userprojectbinding.project)
    _grantaccess(user, dir_reportprepare)


def revokeaccess_project(userprojectbinding):
    user = userprojectbinding.user
    dir_project = dirname.project(userprojectbinding.project)
    _revokeaccess(user, dir_project)
    dir_reportprepare = dirname.report_prepare(userprojectbinding.project)
    _revokeaccess(user, dir_reportprepare)


@background
def garbagedir_project(userprojectbinding): #(project):
    assert userprojectbinding.role == userprojectbinding.RL_CREATOR, "deny garbage collection coz user is not creator"
    project = userprojectbinding.project
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
    dir_correct = dirname.assignment_correct_root(course)
    _mkdir(dir_correct)


def grantaccess_course(usercoursebinding):
    '''
    '''
    course = usercoursebinding.course
    dir_coursepublic = dirname.course_public(course)
    dir_assignmentprepare = dirname.course_assignment_prepare_root(course)
    dir_correct = dirname.assignment_correct_root(course)
    if usercoursebinding.is_teacher:
        _grantaccess(usercoursebinding.user, dir_coursepublic)
        _grantaccess(usercoursebinding.user, dir_assignmentprepare)
        _grantaccess(usercoursebinding.user, dir_correct, acl = 'rXtcy')
    else:
        _grantaccess(usercoursebinding.user, dir_coursepublic, acl = 'rXtcy')


def revokeaccess_course(usercoursebinding):
    '''
    '''
    course = usercoursebinding.course
    dir_coursepublic = dirname.course_public(course)
    dir_assignmentprepare = dirname.course_assignment_prepare_root(course)
    dir_correct = dirname.assignment_correct_root(course)
    _revokeaccess(usercoursebinding.user, dir_coursepublic)
    if usercoursebinding.is_teacher:
        _revokeaccess(usercoursebinding.user, dir_assignmentprepare)
        _revokeaccess(usercoursebinding.user, dir_correct)


###FIXME: def garbagedir_course_share(course):
###FIXME:     dir_course = Dirname.course(course)
###FIXME:     garbage = Filename.course_garbage(course)
###FIXME:     _archivedir(dir_course, garbage)


def get_assignment_prepare_subfolders(course):
    from education.models import Assignment
    dir_assignmentprepare = dirname.course_assignment_prepare_root(course)
    dir_used = [ a.folder for a in Assignment.objects.filter(course = course) ]
    abs_path = lambda x: os.path.join(dir_assignmentprepare, x)
    not_empty_folder = lambda x: os.path.isdir(abs_path(x)) and len(os.listdir(abs_path(x))) > 0 and not x in dir_used
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
    _grantaccess(usercoursebinding.user, dir_workdir)
    if usercoursebinding.is_teacher:
        for studentbinding in usercoursebinding.course.studentbindings:
            dir_assignment_workdir = dirname.assignment_workdir_root(studentbinding)
            _grantaccess(usercoursebinding.user, dir_assignment_workdir, acl = 'rXtcy')
    else:
        dir_assignment_workdir = dirname.assignment_workdir_root(usercoursebinding)
        _mkdir(dir_assignment_workdir)
        _grantaccess(usercoursebinding.user, dir_assignment_workdir)
        for teacherbinding in usercoursebinding.course.teacherbindings:
            _grantaccess(teacherbinding.user, dir_assignment_workdir, acl = 'rXtcy')
#feedback


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

def garbagedir_project(userprojectbinding): #(project):
    assert userprojectbinding.role == userprojectbinding.RL_CREATOR, "deny garbage collection coz user is not creator"
    project = userprojectbinding.project
    dir_project = dirname.project(project)
    garbage = filename.project_garbage(project)
    _archivedir(dir_project, garbage)
    dir_reportprepare = dirname.report_prepare(project)
    _rmdir(dir_reportprepare)

@background
def delete_usercourse(usercoursebinding):
    _rmdir(dirname.assignment_workdir_root(usercoursebinding))
    dir_workdir = dirname.course_workdir(usercoursebinding)
    garbage = filename.course_workdir_garbage(usercoursebinding)
    _archivedir(dir_workdir, garbage)


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
    _chown(dir_target, userassignmentbinding.user.profile.userid, users_gid)
    for teacherbinding in userassignmentbinding.assignment.course.teacherbindings:
        _grantaccess(teacherbinding.user, dir_target, acl = 'rXtcy')


def snapshot_userassignment(userassignmentbinding):
    dir_source = dirname.assignment_workdir(userassignmentbinding)
    if userassignmentbinding.assignment.max_number_of_files:
        n = _count_files(dir_source)
        if n > userassignmentbinding.assignment.max_number_of_files:
            raise Exception(f'Too many files in source folder {dir_source}: {n} > {userassignmentbinding.assignment.max_number_of_files}')
    if userassignmentbinding.assignment.max_size:
        du = _du(dir_source)
        if du > userassignmentbinding.assignment.max_size:
            raise Exception(f'Size exceeded {dir_source}: {du} > {userassignmentbinding.assignment.max_size}')
    archive = filename.assignment_collection(userassignmentbinding)
    _archivedir(dir_source, archive, remove = userassignmentbinding.assignment.remove_collected)
    logger.info(f"+ created {archive} of folder {dir_source}")


def cp_userassignment2correct(userassignmentbinding):
    archivefile = filename.assignment_collection(userassignmentbinding)
    dir_target = dirname.assignment_correct_dir(userassignmentbinding)
    with tarfile.open(archivefile, mode='r') as archive:
        archive.extractall(path = dir_target)
    for teacherbinding in userassignmentbinding.assignment.course.teacherbindings:
        _grantaccess(teacherbinding.user, dir_target)
    logger.info(f"+ extracted {archivefile} in folder {dir_target}")


def cp_userassignment_feedback(userassignmentbinding):
    archivefile = filename.assignment_feedback(userassignmentbinding)
    dir_source = dirname.assignment_correct_dir(userassignmentbinding)
    dir_target = dirname.assignment_feedback_dir(userassignmentbinding)
    _archivedir(dir_source, archivefile, remove = False)
    logger.info(f"+ created {archivefile} of folder {dir_source}")
    with tarfile.open(archivefile, mode='r') as archive:
        archive.extractall(path = dir_target)
    _chown(dir_target, userassignmentbinding.user.profile.userid, users_gid)
    logger.info(f"+ extracted {archivefile} in folder {dir_target}")


#@background
def delete_userassignment(userassignmentbinding):
    dir_assignment = dirname.userassignment_dir(userassignmentbinding)
    if userassignmentbinding.assignment.remove_collected:
        _rmdir(dir_assignment)
    else:
        garbage = filename.assignment_garbage(userassignmentbinding)
        _archivedir(dir_assignment, garbage)
    #FIXME: garbage
    _rmdir(dirname.assignment_correct_dir(userassignmentbinding))
    #FIXME: archive snapshots

