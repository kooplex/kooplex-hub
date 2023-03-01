import os
import time

from hub.lib import dirname

mp_course = dirname.MP.get('course', '/mnt/course')
mp_course_workdir = dirname.MP.get('course_workdir', '/mnt/course_workdir')
mp_course_assignment = dirname.MP.get('course_assignment', '/mnt/course_assignment')

def course_root(course):
    return os.path.join(mp_course, course.folder)

def course_public(course):
    return os.path.join(course_root(course), 'public')

def course_assignment_prepare_root(course):
    return os.path.join(course_root(course), 'assignment_prepare')

def course_assignment_snapshot(course):
    return os.path.join(course_root(course), 'assignment_snapshot')

def assignment_source(assignment):
    return os.path.join(course_assignment_prepare_root(assignment.course), assignment.folder)

def course_workdir_root(course):
    return os.path.join(mp_course_workdir, course.folder)

def course_workdir(usercoursebinding):
    return os.path.join(course_workdir_root(usercoursebinding.course), usercoursebinding.user.username)

def course_assignment_root(course):
    return os.path.join(mp_course_assignment, course.folder)

def assignment_workdir_root(usercoursebinding):
    return os.path.join(course_assignment_root(usercoursebinding.course), 'workdir', usercoursebinding.user.username)

def userassignment_dir(userassignmentbinding):
    from education.models import UserCourseBinding
    ucb = UserCourseBinding.objects.get(user = userassignmentbinding.user, course = userassignmentbinding.assignment.course)
    return os.path.join(assignment_workdir_root(ucb), userassignmentbinding.assignment.folder)
    
def assignment_workdir(userassignmentbinding):
#    return os.path.join(userassignment_dir(userassignmentbinding), 'assignment')
    return userassignment_dir(userassignmentbinding)

def assignment_feedback_dir(userassignmentbinding):
    return os.path.join(userassignment_dir(userassignmentbinding), 'feedback')

def assignment_correct_root(course):
    return os.path.join(course_assignment_root(course), 'correctdir')

def assignment_correct_dir(userassignmentbinding):
    from education.models import UserCourseBinding
    ucb = UserCourseBinding.objects.get(user = userassignmentbinding.user, course = userassignmentbinding.assignment.course)
    return os.path.join(assignment_correct_root(ucb.course), userassignmentbinding.assignment.folder, userassignmentbinding.user.username)

#      def course_garbage(course):
#          return os.path.join(Dirname.mountpoint['garbage'], "course-%s.%f.tar.gz" % (course.folder, time.time()))

def assignment_garbage(userassignmentbinding):
    a = userassignmentbinding.assignment
    return os.path.join(dirname.mp_garbage, userassignmentbinding.user.username, "assignment_%s-%s.%f.tar.gz" % (a.course.folder, a._safename, time.time()))


def course_workdir_garbage(usercoursebinding):
    return os.path.join(dirname.mp_garbage, usercoursebinding.user.username, "course_workdir-%s.%f.tar.gz" % (usercoursebinding.course.folder, time.time()))


def assignment_collection(userassignmentbinding):
    assignment = userassignmentbinding.assignment
    return os.path.join(course_assignment_snapshot(assignment.course), 'collection-%s-%s.%d.tar.gz' % (assignment._safename, userassignmentbinding.user.username, userassignmentbinding.submitted_at.timestamp()))


def assignment_feedback(userassignmentbinding):
    assignment = userassignmentbinding.assignment
    return os.path.join(course_assignment_snapshot(assignment.course), 'feedback-%s-%s-%s.%d.tar.gz' % (assignment._safename, userassignmentbinding.user.username, userassignmentbinding.corrector.username, userassignmentbinding.corrected_at.timestamp()))


#      @staticmethod
#      def assignmentsnapshot_garbage(assignment):
#          return os.path.join(Dirname.mountpoint['garbage'], 'assignmentsnapshot-%s-%s-%s-%f.tar.gz' % (assignment.coursecode.course.folder, assignment.safename, assignment.created_at.timestamp(), time.time()))
  

def get_assignment_prepare_subfolders(course):
    from education.models import Assignment
    dir_assignmentprepare = course_assignment_prepare_root(course)
    dir_used = [ a.folder for a in Assignment.objects.filter(course = course) ]
    abs_path = lambda x: os.path.join(dir_assignmentprepare, x)
    not_empty_folder = lambda x: os.path.isdir(abs_path(x)) and len(os.listdir(abs_path(x))) > 0 and not x in dir_used
    return list(filter(not_empty_folder, os.listdir(dir_assignmentprepare)))
