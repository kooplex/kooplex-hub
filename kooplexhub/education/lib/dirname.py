import os

from ..conf import EDUCATION_SETTINGS

mp_course = EDUCATION_SETTINGS["mounts"]["workdir"]["mountpoint_hub"] #FIXME
#mp_course = MP.get('course', '/mnt/course')
mp_course_workdir = EDUCATION_SETTINGS["mounts"]["workdir"]["mountpoint_hub"]
mp_course_assignment = EDUCATION_SETTINGS["mounts"]["assignment"]["mountpoint_hub"]

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
    #return os.path.join(userassignment_dir(userassignmentbinding), 'assignment')
    return userassignment_dir(userassignmentbinding)

def assignment_feedback_dir(userassignmentbinding):
    return os.path.join(userassignment_dir(userassignmentbinding), 'feedback')

def assignment_correct_root(course):
    return os.path.join(course_assignment_root(course), 'correctdir')

def assignment_correct_dir(userassignmentbinding):
    from education.models import UserCourseBinding
    ucb = UserCourseBinding.objects.get(user = userassignmentbinding.user, course = userassignmentbinding.assignment.course)
    return os.path.join(assignment_correct_root(ucb.course), userassignmentbinding.assignment.folder, userassignmentbinding.user.username)

