import os
import time

from .conf import EDUCATION_SETTINGS

def course_public(course):
    return os.path.join(
        EDUCATION_SETTINGS["mounts"]["public"]["mountpoint_hub"],
        EDUCATION_SETTINGS["mounts"]["public"]["folder"].format(course=course),
    )

def course_assignment_prepare_root(course):
    return os.path.join(
        EDUCATION_SETTINGS["mounts"]["assignment_prepare"]["mountpoint_hub"],
        EDUCATION_SETTINGS["mounts"]["assignment_prepare"]["folder"].format(course=course),
    )

def course_assignment_snapshot(course): #FIXME: find a better name
    return os.path.join(
        EDUCATION_SETTINGS["mounts"]["assignment_snapshot"]["mountpoint_hub"],
        EDUCATION_SETTINGS["mounts"]["assignment_snapshot"]["folder"].format(course=course),
    )

def assignment_source(assignment):
    return os.path.join(course_assignment_prepare_root(assignment.course), assignment.folder)

def course_workdir_root(course):
    return os.path.join(
        EDUCATION_SETTINGS["mounts"]["workdir"]["mountpoint_hub"],
        EDUCATION_SETTINGS["mounts"]["workdir"]["folder_top"].format(course=course),
    )

def course_workdir(usercoursebinding):
    return os.path.join(
        EDUCATION_SETTINGS["mounts"]["workdir"]["mountpoint_hub"],
        EDUCATION_SETTINGS["mounts"]["workdir"]["folder"].format(course=course, user=usercoursebinding.user),
    )

def course_assignment_root(course):
    return os.path.join(
        EDUCATION_SETTINGS["mounts"]["assignment"]["mountpoint_hub"],
        EDUCATION_SETTINGS["mounts"]["assignment"]["folder_top"].format(course=course),
    )

def assignment_workdir_root(usercoursebinding):
    return os.path.join(
        EDUCATION_SETTINGS["mounts"]["assignment"]["mountpoint_hub"],
        EDUCATION_SETTINGS["mounts"]["assignment"]["folder"].format(course=usercoursebinding.course, user=usercoursebinding.user),
    )

def assignment_workdir(userassignmentbinding):
    #FIXME: use relat
    from education.models import UserCourseBinding
    ucb = UserCourseBinding.objects.filter(user = userassignmentbinding.user, course = userassignmentbinding.assignment.course).first()
    return os.path.join(assignment_workdir_root(ucb), userassignmentbinding.assignment.folder) if ucb else None
    
def assignment_feedback_dir(userassignmentbinding):
    return os.path.join(assignment_workdir(userassignmentbinding), 'feedback')

def assignment_correct_root(course):
    return os.path.join(course_assignment_root(course), 'correctdir')

def assignment_correct_dir(userassignmentbinding):
    from education.models import UserCourseBinding
    ucb = UserCourseBinding.objects.filter(user = userassignmentbinding.user, course = userassignmentbinding.assignment.course).first()
    return os.path.join(assignment_correct_root(ucb.course), userassignmentbinding.assignment.folder, userassignmentbinding.user.username) if ucb else None

#FIXME def course_garbage(course):
#FIXME     return os.path.join(mp_garbage, "course-%s.%f.tar.gz" % (course.folder, time.time()))

#FIXME def assignment_garbage(userassignmentbinding):
#FIXME     a = userassignmentbinding.assignment
#FIXME     return os.path.join(mp_garbage, userassignmentbinding.user.username, "assignment_%s-%s.%f.tar.gz" % (a.course.folder, a._safename, time.time()))


#FIXME def course_workdir_garbage(usercoursebinding):
#FIXME     return os.path.join(mp_garbage, usercoursebinding.user.username, "course_workdir-%s.%f.tar.gz" % (usercoursebinding.course.folder, time.time()))

def assignment_snapshot(assignment):
    return os.path.join(
        course_assignment_snapshot(assignment.course), 
        f'assignment-snapshot-{assignment._safename}.{time.time()}.tar.gz',
    )


def assignment_collection(userassignmentbinding):
    assignment = userassignmentbinding.assignment
    return os.path.join(
        course_assignment_snapshot(assignment.course), 
        'collection-%s-%s.%d.tar.gz' % (assignment._safename, userassignmentbinding.user.username, userassignmentbinding.last_submitted_at.timestamp()),
    )


def assignment_feedback(userassignmentbinding):
    assignment = userassignmentbinding.assignment
    return os.path.join(
        course_assignment_snapshot(assignment.course), 
        'feedback-%s-%s-%s.%d.tar.gz' % (assignment._safename, userassignmentbinding.user.username, userassignmentbinding.corrector.username, userassignmentbinding.corrected_at.timestamp())
    )


#      def assignmentsnapshot_garbage(assignment):
#          return os.path.join(Dirname.mountpoint['garbage'], 'assignmentsnapshot-%s-%s-%s-%f.tar.gz' % (assignment.coursecode.course.folder, assignment.safename, assignment.created_at.timestamp(), time.time()))
  

def get_assignment_prepare_subfolders(course):
    from education.models import Assignment
    dir_assignmentprepare = course_assignment_prepare_root(course)
    dir_used = [ a.folder for a in Assignment.objects.filter(course = course) ]
    abs_path = lambda x: os.path.join(dir_assignmentprepare, x)
    not_empty_folder = lambda x: os.path.isdir(abs_path(x)) and len(os.listdir(abs_path(x))) > 0 and not x in dir_used
    return list(filter(not_empty_folder, os.listdir(dir_assignmentprepare)))
