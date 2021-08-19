import os
import logging

try:
    from kooplexhub.settings import KOOPLEX
except ImportError:
    KOOPLEX = {}

logger = logging.getLogger(__name__)

MP = KOOPLEX.get('mountpoint_hub', {})

mp_home = MP.get('home', '/mnt/home')
mp_garbage = MP.get('garbage', '/mnt/garbage')

mp_project = MP.get('project', '/mnt/project')

mp_report = MP.get('report', '/mnt/report')
mp_report_prepare = MP.get('report_prepare', '/mnt/report_prepare')

mp_course = MP.get('course', '/mnt/course')
mp_course_workdir = MP.get('course_workdir', '/mnt/course_workdir')
mp_course_assignment = MP.get('course_assignment', '/mnt/course_assignment')

def userhome(user):
    return os.path.join(mp_home, user.username)

def usergarbage(user):
    return os.path.join(mp_garbage, user.username)

def project(project):
    return os.path.join(mp_project, project.uniquename)

def report_prepare(project):
    return os.path.join(mp_report_prepare, project.uniquename)

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
    return os.path.join(userassignment_dir(userassignmentbinding), 'assignment')

def assignment_feedback_dir(userassignmentbinding):
    return os.path.join(userassignment_dir(userassignmentbinding), 'feedback')

def assignment_correct_dir(userassignmentbinding):
    from education.models import UserCourseBinding
    ucb = UserCourseBinding.objects.get(user = userassignmentbinding.user, course = userassignmentbinding.assignment.course)
    return os.path.join(course_assignment_root(ucb.course), 'correctdir', userassignmentbinding.assignment.folder, userassignmentbinding.user.username)

