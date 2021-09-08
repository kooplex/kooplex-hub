import os
import time

from ..lib import dirname
try:
    from kooplexhub.settings import KOOPLEX
except ImportError:
    KOOPLEX = {}

def userhome_garbage(user):
    return os.path.join(dirname.mp_garbage, "user-%s.%f.tar.gz" % (user.username, time.time()))

def project_garbage(project):
    return os.path.join(dirname.mp_garbage, project.creator.username, "project-%s.%f.tar.gz" % (project.uniquename, time.time()))
  
#      @staticmethod
#      def course_garbage(course):
#          return os.path.join(Dirname.mountpoint['garbage'], "course-%s.%f.tar.gz" % (course.folder, time.time()))
#  
#      @staticmethod
#      def courseworkdir_archive(usercoursebinding):
#          return os.path.join(Dirname.mountpoint['home'], usercoursebinding.user.username, "garbage", "%s.%f.tar.gz" % (usercoursebinding.course.folder, time.time()))


def assignment_snapshot(assignment):
    return os.path.join(dirname.course_assignment_snapshot(assignment.course), 'assignment-snapshot-%s.%d.tar.gz' % (assignment.safename, assignment.created_at.timestamp()))


def assignment_collection(userassignmentbinding):
    assignment = userassignmentbinding.assignment
    return os.path.join(dirname.course_assignment_snapshot(assignment.course), 'collection-%s-%s.%d.tar.gz' % (assignment.safename, userassignmentbinding.user.username, userassignmentbinding.submitted_at.timestamp()))


def assignment_feedback(userassignmentbinding):
    assignment = userassignmentbinding.assignment
    return os.path.join(dirname.course_assignment_snapshot(assignment.course), 'feedback-%s-%s-%s.%d.tar.gz' % (assignment.safename, userassignmentbinding.user.username, userassignmentbinding.corrector.username, userassignmentbinding.corrected_at.timestamp()))


#      @staticmethod
#      def assignmentsnapshot_garbage(assignment):
#          return os.path.join(Dirname.mountpoint['garbage'], 'assignmentsnapshot-%s-%s-%s-%f.tar.gz' % (assignment.coursecode.course.folder, assignment.safename, assignment.created_at.timestamp(), time.time()))
  

