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
import tarfile

from kooplex.lib import bash
from kooplex.settings import KOOPLEX

logger = logging.getLogger(__name__)

class Dirname:
    mountpoint = KOOPLEX.get('mountpoint', {})

    @staticmethod
    def userhome(user):
        return os.path.join(Dirname.mountpoint['home'], user.username)

    @staticmethod
    def userhome_garbage(user):
        return os.path.join(Dirname.mountpoint['garbage'], "user-%s.%f.tar.gz" % (user.username, time.time()))

    @staticmethod
    def course(course):
        return os.path.join(Dirname.mountpoint['course'], course.safecourseid)

    @staticmethod
    def course_garbage(course):
        return os.path.join(Dirname.mountpoint['garbage'], "course-%s.%f.tar.gz" % (course.safecourseid, time.time()))

    @staticmethod
    def courseprivate(course):
        return os.path.join(Dirname.course(course), 'private')

    @staticmethod
    def coursepublic(course):
        return os.path.join(Dirname.course(course), 'public')

    @staticmethod
    def courseworkdir(usercoursebinding):
        flag = usercoursebinding.flag if usercoursebinding.flag else '_'
        return os.path.join(Dirname.mountpoint['usercourse'], usercoursebinding.course.safecourseid, flag) if usercoursebinding.is_teacher else \
               os.path.join(Dirname.mountpoint['usercourse'], usercoursebinding.course.safecourseid, flag, usercoursebinding.user.username)

    @staticmethod
    def courseworkdir_archive(usercoursebinding):
        flag = usercoursebinding.flag if usercoursebinding.flag else '_'
        return os.path.join(Dirname.mountpoint['home'], usercoursebinding.user.username, "%s.%s.%f.tar.gz" % (usercoursebinding.course.safecourseid, flag, time.time()))

    @staticmethod
    def assignmentsource(assignment):
        return os.path.join(Dirname.courseprivate(assignment.course), assignment.folder)

    @staticmethod
    def assignmentsnapshot(assignment):
        flag = assignment.flag if assignment.flag else '_'
        return os.path.join(Dirname.mountpoint['assignment'], assignment.course.safecourseid, flag, 'assignmentsnapshot-%s.%d.tar.gz' % (assignment.safename, assignment.created_at.timestamp()))

    @staticmethod
    def assignmentsnapshot_garbage(assignment):
        flag = assignment.flag if assignment.flag else '_'
        return os.path.join(Dirname.mountpoint['garbage'], 'assignmentsnapshot-%s.%s-%s.%d-%f.tar.gz' % (assignment.course.safecourseid, flag, assignment.safename, assignment.created_at.timestamp(), time.time()))

    @staticmethod
    def assignmentworkdir(userassignmentbinding):
        from hub.models import UserCourseBinding
        usercoursebinding = UserCourseBinding.objects.get(user = userassignmentbinding.user, course = userassignmentbinding.assignment.course, flag = userassignmentbinding.assignment.flag)
        wd = Dirname.courseworkdir(usercoursebinding)
        return os.path.join(wd, userassignmentbinding.assignment.safename)

    @staticmethod
    def assignmentcollectdir(userassignmentbinding, in_hub = True): #TODO: refactor
        assignment = userassignmentbinding.assignment
        flag = assignment.flag if assignment.flag else '_'
        return os.path.join(Dirname.mountpoint['assignment'], assignment.course.safecourseid, flag, 'submitted-%s-%s.%d.tar.gz' % (assignment.safename, userassignmentbinding.user.username, userassignmentbinding.submitted_at.timestamp())) if in_hub else \
               os.path.join('assignment', assignment.course.safecourseid, flag, 'submitted-%s-%s.%d.tar.gz' % (assignment.safename, userassignmentbinding.user.username, userassignmentbinding.submitted_at.timestamp()))

    @staticmethod
    def assignmentcorrectdir(userassignmentbinding, in_hub = True):
        assignment = userassignmentbinding.assignment
        flag = assignment.flag if assignment.flag else '_'
        return os.path.join(Dirname.mountpoint['assignment'], assignment.course.safecourseid, flag, 'feedback-%s-%s.%d' % (assignment.safename, userassignmentbinding.user.username, userassignmentbinding.submitted_at.timestamp())) if in_hub else \
               os.path.join('assignment', assignment.course.safecourseid, flag, 'feedback-%s-%s.%d' % (assignment.safename, userassignmentbinding.user.username, userassignmentbinding.submitted_at.timestamp()))


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
    @type mountpoint: bool
    """
    logger.debug("dir: %s uid/gid: %d/%d; mountpoint: %s" % (path, uid, gid, mountpoint))
    dir_util.mkpath(path)
    os.chown(path, uid, gid)
    os.chmod(path, mode)
    if mountpoint:
        placeholder = os.path.join(path, '_not_mounted_')
        open(placeholder, 'w').close()
        os.chown(placeholder, 0, 0)
        os.chmod(placeholder, 0)

def _archivedir(folder, target, remove = True):
    if not os.path.exists(folder):
        logger.warning("Folder %s is missing" % folder)
        return
    try:
        dir_util.mkpath(os.path.dirname(target))
        with tarfile.open(target, mode='w:gz') as archive:
            archive.add(folder, arcname = '.', recursive = True)
    except Exception as e:
        logger.error("Cannot create archive %s -- %s" % (folder, e))
    finally:
        if remove:
            dir_util.remove_tree(folder)
            logger.debug("Folder %s removed" % folder)

def mkdir_home(user):
    """
    @summary: create a home directory for the user
    @param user: the user
    @type user: kooplex.hub.models.User
    """
    try:
        dir_home = Dirname.userhome(user)
        _mkdir(dir_home, uid = user.profile.userid, gid = user.profile.groupid)
        dir_condaenv = os.path.join(dir_home, '.conda', 'envs')
        _mkdir(dir_condaenv, uid = user.profile.userid, gid = user.profile.groupid, mode = 0o700)
        dir_share = os.path.join(dir_home, 'share')
        _mkdir(dir_share, mountpoint = True, mode = 0o000)
        dir_workdir = os.path.join(dir_home, 'workdir')
        _mkdir(dir_workdir, mountpoint = True, mode = 0o000)
        dir_reportdir = os.path.join(dir_home, 'report')
        _mkdir(dir_reportdir, mountpoint = True, mode = 0o000)
        logger.info("Home dir structure created for user %s" % user)
    except KeyError as e:
        logger.error("Cannot create home dir, KOOPLEX['mountpoint']['home'] is missing")

def garbagedir_home(user):
    dir_home = Dirname.userhome(user)
    garbage = Dirname.userhome_garbage(user)
    _archivedir(dir_home, garbage)

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
        if usercoursebinding.is_teacher:
            bash("setfacl -R -m u:%d:rwX %s" % (usercoursebinding.user.profile.userid, dir_coursepublic))
        logger.debug("acl granted %s" % usercoursebinding)
    except Exception as e:
        logger.error("Cannot grant acl %s -- %s" % (usercoursebinding, e))

def revokeacl_course_share(usercoursebinding):
    try:
        dir_coursepublic = Dirname.coursepublic(usercoursebinding.course)
        if usercoursebinding.is_teacher:
            bash("setfacl -R -x u:%d %s" % (usercoursebinding.user.profile.userid, dir_coursepublic))
        logger.debug("acl revoked %s" % usercoursebinding)
    except Exception as e:
        logger.error("Cannot revoke acl %s -- %s" % (usercoursebinding, e))

def garbagedir_course_share(course):
    dir_course = Dirname.course(course)
    garbage = Dirname.course_garbage(course)
    _archivedir(dir_course, garbage)

def mkdir_course_workdir(usercoursebinding):
    try:
        dir_usercourse = Dirname.courseworkdir(usercoursebinding)
        uid = 0 if usercoursebinding.is_teacher else usercoursebinding.user.profile.userid
        _mkdir(dir_usercourse, uid = uid, gid = usercoursebinding.course.groupid, mode = 0o770)
    except KeyError as e:
        logger.error("Cannot create course dir, KOOPLEX['mountpoint']['usercourse'] is missing")

def grantacl_course_workdir(usercoursebinding):
    try:
        if usercoursebinding.is_teacher:
            dir_usercourse = Dirname.courseworkdir(usercoursebinding)
            bash("setfacl -R -m u:%d:rwX %s" % (usercoursebinding.user.profile.userid, dir_usercourse))
    except Exception as e:
        logger.error("Cannot grant acl %s -- %s" % (usercoursebinding, e))

def revokeacl_course_workdir(usercoursebinding):
    try:
        if usercoursebinding.is_teacher:
            dir_usercourse = Dirname.courseworkdir(usercoursebinding)
            bash("setfacl -R -x u:%d %s" % (usercoursebinding.user.profile.userid, dir_usercourse))
    except Exception as e:
        logger.error("Cannot revoke acl %s -- %s" % (usercoursebinding, e))

def archive_course_workdir(usercoursebinding):
    if usercoursebinding.is_teacher:
        return
    dir_usercourse = Dirname.courseworkdir(usercoursebinding)
    archive = Dirname.courseworkdir_archive(usercoursebinding)
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
    archive = Dirname.assignmentsnapshot(assignment)
    _archivedir(dir_source, archive, remove = False)

def garbagedir_assignmentsnapshot(assignment):
    try:
        archive = Dirname.assignmentsnapshot(assignment)
        garbage = Dirname.assignmentsnapshot_garbage(assignment)
        file_util.move_file(archive, garbage)
    except Exception as e:
        logger.error("move %s -> %s fails -- %s" % (archive, garbage, e))

def cp_assignmentsnapshot(userassignmentbinding):
    try:
        archivefile = Dirname.assignmentsnapshot(userassignmentbinding.assignment)
        dir_target = Dirname.assignmentworkdir(userassignmentbinding)
        with tarfile.open(archivefile, mode='r') as archive:
            archive.extractall(path = dir_target)
        bash("setfacl -R -m u:%d:rwX %s" % (userassignmentbinding.user.profile.userid, dir_target))
    except Exception as e:
        logger.error("Cannot cp snapshot dir %s -- %s" % (userassignmentbinding, e))

def cp_userassignment(userassignmentbinding):
    dir_source = Dirname.assignmentworkdir(userassignmentbinding)
    archive = Dirname.assignmentcollectdir(userassignmentbinding)
    _archivedir(dir_source, archive, remove = False)
        #bash("chmod -R 0 %s" % dir_target)
        #bash("setfacl -R -m u:%d:rX %s" % (userassignmentbinding.user.profile.userid, dir_target))

def cp_userassignment2correct(userassignmentbinding):
    try:
        archivefile = Dirname.assignmentcollectdir(userassignmentbinding)
        dir_target = Dirname.assignmentcorrectdir(userassignmentbinding)
        with tarfile.open(archivefile, mode='r') as archive:
            archive.extractall(path = dir_target)
#        bash("chmod -R 0 %s" % dir_target)
        bash("setfacl -R -m u:%d:rwX %s" % (userassignmentbinding.corrector.profile.userid, dir_target))
    except Exception as e:
        logger.error("Cannot copy correct dir %s -- %s" % (userassignmentbinding, e))

def manageacl_feedback(userassignmentbinding):
    try:
        dir_target = Dirname.assignmentcorrectdir(userassignmentbinding)
#        bash("setfacl -R -x u:%d %s" % (userassignmentbinding.corrector.profile.userid, dir_target))
#        bash("setfacl -R -m u:%d:rX %s" % (userassignmentbinding.corrector.profile.userid, dir_target))
        bash("setfacl -R -m u:%d:rX %s" % (userassignmentbinding.user.profile.userid, dir_target))
    except Exception as e:
        logger.error("Cannot revoke acl from feedback dir %s -- %s" % (userassignmentbinding, e))

