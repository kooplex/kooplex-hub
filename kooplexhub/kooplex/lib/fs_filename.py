import os
import time

from .fs_dirname import Dirname
from kooplex.settings import KOOPLEX

class Filename:
    mountpoint = KOOPLEX.get('mountpoint', {})

    @staticmethod
    def userhome_garbage(user):
        return os.path.join(Dirname.mountpoint['garbage'], "user-%s.%f.tar.gz" % (user.username, time.time()))

    @staticmethod
    def share_garbage(userprojectbinding):
        return os.path.join(Dirname.mountpoint['garbage'], "projectshare-%s.%f.tar.gz" % (userprojectbinding.project.uniquename, time.time()))

    @staticmethod
    def workdir_archive(userprojectbinding):
        return os.path.join(Dirname.mountpoint['home'], userprojectbinding.user.username, "garbage", "workdir-%s.%f.tar.gz" % (userprojectbinding.uniquename, time.time()))

    @staticmethod
    def vcpcache_archive(vcproject):
        return os.path.join(Dirname.mountpoint['home'], vcproject.token.user.username, "garbage", "git-%s.%f.tar.gz" % (vcproject.uniquename, time.time()))

    @staticmethod
    def course_garbage(course):
        return os.path.join(Dirname.mountpoint['garbage'], "course-%s.%f.tar.gz" % (course.folder, time.time()))

    @staticmethod
    def courseworkdir_archive(usercoursebinding):
        return os.path.join(Dirname.mountpoint['home'], usercoursebinding.user.username, "garbage", "%s.%f.tar.gz" % (usercoursebinding.course.folder, time.time()))

    @staticmethod
    def assignmentsnapshot(assignment):
        return os.path.join(Dirname.mountpoint['assignment'], assignment.coursecode.course.folder, 'assignmentsnapshot-%s.%d.tar.gz' % (assignment.safename, assignment.created_at.timestamp()))

    @staticmethod
    def assignmentsnapshot_garbage(assignment):
        return os.path.join(Dirname.mountpoint['garbage'], 'assignmentsnapshot-%s-%s-%s-%f.tar.gz' % (assignment.coursecode.course.folder, assignment.safename, assignment.created_at.timestamp(), time.time()))

    @staticmethod
    def assignmentcollection(userassignmentbinding):
        assignment = userassignmentbinding.assignment
        return os.path.join(Dirname.mountpoint['assignment'], assignment.coursecode.course.fodler, 'submitted-%s-%s.%d.tar.gz' % (assignment.safename, userassignmentbinding.user.username, userassignmentbinding.submitted_at.timestamp()))


