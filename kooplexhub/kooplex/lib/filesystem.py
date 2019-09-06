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

from kooplex.lib import bash, Dirname, Filename

logger = logging.getLogger(__name__)

def _mkdir(path, uid = 0, gid = 0, mode = 0b111101000):
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
    """
    logger.debug("dir: %s uid/gid: %d/%d" % (path, uid, gid))
    dir_util.mkpath(path)
    os.chown(path, uid, gid)
    os.chmod(path, mode)


def _grantaccess(user, folder, acl = 'rwX'):
    bash("setfacl -R -m u:%d:%s %s" % (user.profile.userid, acl, folder))

def _revokeaccess(user, folder):
    bash("setfacl -R -x u:%d %s" % (user.profile.userid, folder))


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
        logger.error("Cannot create archive %s -- %s" % (folder, e))
    finally:
        if remove:
            dir_util.remove_tree(folder)
            logger.debug("Folder %s removed" % folder)

def _copy_dir(f_source, f_target, remove = False):
    if not os.path.exists(f_source):
        msg = "Folder %s not found" % f_source
        logger.error(msg)
        raise Exception(msg)
    dir_util.copy_tree(f_source, f_target)
    logger.info("copied %s -> %s" % (f_source, f_target))
    if remove:
        dir_util.remove_tree(f_source)
        logger.debug("Folder %s removed" % folder)
    


def _createfile(fn, content, uid = 0, gid = 0, mode = 0b111101000):
    with open(fn, 'w') as f:
        f.write(content)
    os.chown(fn, uid, gid)
    os.chmod(fn, mode)
    logger.info("Created file: %s" % fn)

########################################


def check_home(user):
    dir_home = Dirname.userhome(user)
    assert os.path.exists(dir_home), "Folder %s does not exist" % dir_home
#TODO: check permissions

def mkdir_home(user):
    """
    @summary: create a home directory for the user
    @param user: the user
    @type user: kooplex.hub.models.User
    """
    dir_home = Dirname.userhome(user)
    _mkdir(dir_home, uid = user.profile.userid, gid = user.profile.groupid)

def garbagedir_home(user):
    dir_home = Dirname.userhome(user)
    garbage = Filename.userhome_garbage(user)
    _archivedir(dir_home, garbage)

########################################

def check_usergarbage(user):
    dir_usergarbage = Dirname.usergarbage(user)
    assert os.path.exists(dir_usergarbage), "Folder %s does not exist" % dir_usergarbage

def mkdir_usergarbage(user):
    dir_usergarbage = Dirname.usergarbage(user)
    _mkdir(dir_usergarbage, uid = user.profile.userid, gid = user.profile.groupid)


########################################

def check_reportprepare(user):
    dir_reportprepare = Dirname.reportprepare(user)
    assert os.path.exists(dir_reportprepare), "Folder %s does not exist" % dir_reportprepare

def mkdir_reportprepare(user):
    dir_reportprepare = Dirname.reportprepare(user)
    _mkdir(dir_reportprepare, uid = user.profile.userid, gid = user.profile.groupid)

def snapshot_report(report):
    dir_source = os.path.join(Dirname.reportprepare(report.creator), report.folder)
    dir_target = Dirname.report(report)
    _copy_dir(dir_source, dir_target, remove = False)
    dir_reportroot = Dirname.reportroot(report.creator)
    _grantaccess(report.creator, dir_reportroot, acl = 'rX')

def garbage_report(report):
    dir_source = Dirname.report(report)
    garbage = Filename.report_garbage(report)
    _archivedir(dir_source, garbage, remove = True)

def prepare_dashboardreport_withinitcell(report):
    import json
    fn = os.path.join(Dirname.report(report), report.index)
    d=json.load(open(fn))
    for ic in range(len(d['cells'])):
        d['cells'][ic]['metadata']['init_cell']=True

    # Get rid of unnecessray info    
    kernel = d['metadata']['kernelspec']
    language = d['metadata']['language_info']
    d['metadata'].clear()
    d['metadata']['kernelspec'] = kernel
    d['metadata']['language_info'] = language
    json.dump(d, open(fn, 'w'))



########################################


def mkdir_share(userprojectbinding):
    project = userprojectbinding.project
    dir_share = Dirname.share(userprojectbinding)
    _mkdir(dir_share, uid = project.fs_uid, gid = project.fs_gid)

def garbagedir_share(userprojectbinding):
    dir_share = Dirname.share(userprojectbinding)
    garbage = Filename.share_garbage(userprojectbinding)
    _archivedir(dir_share, garbage)


def grantaccess_share(userprojectbinding):
    user = userprojectbinding.user
    dir_share = Dirname.share(userprojectbinding)
    _grantaccess(user, dir_share)

def revokeaccess_share(userprojectbinding):
    user = userprojectbinding.user
    dir_share = Dirname.share(userprojectbinding)
    _revokeaccess(user, dir_share)


def mkdir_workdir(userprojectbinding):
    dir_workdir = Dirname.workdir(userprojectbinding)
    _mkdir(dir_workdir, uid = userprojectbinding.user.profile.userid, gid = userprojectbinding.user.profile.groupid)

def archivedir_workdir(userprojectbinding):
    dir_workdir = Dirname.workdir(userprojectbinding)
    target = Filename.workdir_archive(userprojectbinding)
    _archivedir(dir_workdir, target)


def mkdir_vcpcache(vcprojectprojectbinding):
    profile = vcprojectprojectbinding.vcproject.token.user.profile
    dir_cache = Dirname.vcpcache(vcprojectprojectbinding.vcproject)
    _mkdir(dir_cache, uid = profile.userid, gid = profile.groupid)
    clonescript_vcpcache(vcprojectprojectbinding)

def clonescript_vcpcache(vcprojectprojectbinding):
    vcp = vcprojectprojectbinding.vcproject
    profile = vcp.token.user.profile
    dir_target = Dirname.vcpcache(vcprojectprojectbinding.vcproject)
    fn_script = os.path.join(dir_target, "clone.sh")
    script = """
#! /bin/bash

set -v

mv $0 $(mktemp)

git clone ssh://git@%s/%s %s
    """ % (vcp.token.repository.domain, vcp.project_name, dir_target)
    _createfile(fn_script, script, uid = profile.userid, gid = profile.groupid)

def archivedir_vcpcache(vcproject):
    dir_cache = Dirname.vcpcache(vcproject)
    target = Filename.vcpcache_archive(vcproject)
    _archivedir(dir_cache, target)


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


