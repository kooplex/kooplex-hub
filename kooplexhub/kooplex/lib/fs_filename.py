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
    def project_garbage(project):
        return os.path.join(Dirname.mountpoint['garbage'], "project-%s.%f.tar.gz" % (project.uniquename, time.time()))

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
        return os.path.join(Dirname.mountpoint['assignment'], assignment.coursecode.course.folder, 'submitted-%s-%s.%d.tar.gz' % (assignment.safename, userassignmentbinding.user.username, userassignmentbinding.submitted_at.timestamp()))

    @staticmethod
    def report_garbage(report):
        return os.path.join(Dirname.mountpoint['garbage'], report.creator.username, "report-%s-%s.%f.tar.gz" % (report.name, report.ts_human, time.time()))

