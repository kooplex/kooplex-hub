import os
import time

from .conf import EDUCATION_SETTINGS
from .models import Assignment

def course_public(course):
    return os.path.join(
        EDUCATION_SETTINGS.mounts.public.mountpoint_hub,
        EDUCATION_SETTINGS.mounts.public.folder.format(course=course),
    )

def course_assignment_prepare_root(course):
    return os.path.join(
        EDUCATION_SETTINGS.mounts.prepare.mountpoint_hub,
        EDUCATION_SETTINGS.mounts.prepare.folder.format(course=course),
    )

def course_assignment_snapshot(course): #FIXME: find a better name
    return os.path.join(
        EDUCATION_SETTINGS.mounts.snapshot.mountpoint_hub,
        EDUCATION_SETTINGS.mounts.snapshot.folder.format(course=course),
    )

def assignment_source(assignment):
    return os.path.join(
        course_assignment_prepare_root(
            assignment.course
        ),
        assignment.folder,
    )



def course_workdir_root(course):
    return os.path.join(
        EDUCATION_SETTINGS.mounts.workdir.mountpoint_hub,
        EDUCATION_SETTINGS.mounts.workdir.folder_top.format(course=course),
    )

def course_workdir(usercoursebinding):
    return os.path.join(
        EDUCATION_SETTINGS.mounts.workdir.mountpoint_hub,
        EDUCATION_SETTINGS.mounts.workdir.folder.format(course=course, user=usercoursebinding.user),
    )

def course_assignment_root(course):
    return os.path.join(
        EDUCATION_SETTINGS.mounts.assignment.mountpoint_hub,
        EDUCATION_SETTINGS.mounts.assignment.folder_top.format(course=course),
    )

def assignment_workdir_root(usercoursebinding):
    return os.path.join(
        EDUCATION_SETTINGS.mounts.assignment.mountpoint_hub,
        EDUCATION_SETTINGS.mounts.assignment.folder.format(course=usercoursebinding.course, user=usercoursebinding.user),
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
    ucb = (
        UserCourseBinding.objects
        .filter(
            user=userassignmentbinding.user, 
            course=userassignmentbinding.assignment.course
        )
        .first()
    )
    return os.path.join(
        assignment_correct_root(ucb.course), 
        userassignmentbinding.assignment.folder, 
        userassignmentbinding.user.username
    ) if ucb else None

def course_public_garbage(course):
    return os.path.join(
        HUB_SETTINGS.mounts.garbage.mountpoint_hub,
        EDUCATION_SETTINGS.mounts.public.garbage.format(course=course, time=time.time()),
    )

def course_assignment_prepare_garbage(course):
    return os.path.join(
        HUB_SETTINGS.mounts.garbage.mountpoint_hub,
        EDUCATION_SETTINGS.mounts.prepare.garbage.format(course=course, time=time.time()),
    )

def assignment_garbage(userassignmentbinding):
    a = userassignmentbinding.assignment
    return os.path.join(
        HUB_SETTINGS.mounts.garbage.mountpoint_hub,
        EDUCATION_SETTINGS.mounts.assignment.garbage.format(course=a.course, user=userassignmentbinding.user, assignment=a, time=time.time()),
    )


def course_workdir_garbage(usercoursebinding):
    return os.path.join(
        HUB_SETTINGS.mounts.garbage.mountpoint_hub,
        EDUCATION_SETTINGS.mounts.workdir.garbage.format(course=usercoursebinding.course, user=usercoursebinding.user, time=time.time()),
    )

def assignment_snapshot_archive(assignment):
    return os.path.join(
        course_assignment_snapshot(assignment.course), 
        EDUCATION_SETTINGS.mounts.snapshot.snapshot_name.format(
            assignment=assignment, 
            time=time.time()
        ),
    )


def assignment_collection_archive(userassignmentbinding):
    assignment = userassignmentbinding.assignment
    return os.path.join(
        course_assignment_snapshot(assignment.course), 
        EDUCATION_SETTINGS.mounts.snapshot.collection_name.format(
            assignment=assignment, 
            user=userassignmentbinding.user, 
            time=userassignmentbinding.last_submitted_at.timestamp()
        ),
    )


def assignment_feedback(userassignmentbinding):
    assignment = userassignmentbinding.assignment
    return os.path.join(
        course_assignment_snapshot(assignment.course), 
        EDUCATION_SETTINGS.mounts.snapshot.feedback_name.format(
            assignment=assignment, 
            user=userassignmentbinding.user, 
            time=userassignmentbinding.corrected_at.timestamp()
        ),
    )


#      def assignmentsnapshot_garbage(assignment):
#          return os.path.join(Dirname.mountpoint['garbage'], 'assignmentsnapshot-%s-%s-%s-%f.tar.gz' % (assignment.coursecode.course.folder, assignment.safename, assignment.created_at.timestamp(), time.time()))
  

def get_assignment_prepare_subfolders(
    course,
):
    root = course_assignment_prepare_root(
        course
    )

    if not os.path.isdir(root):
        return []

    used = set(
        Assignment.objects
        .filter(course=course)
        .values_list(
            "folder",
            flat=True,
        )
    )

    result = []

    for name in os.listdir(root):
        path = os.path.join(
            root,
            name,
        )

        if name in used:
            continue

        if not os.path.isdir(path):
            continue

        if not os.listdir(path):
            continue

        result.append(name)

    return sorted(
        result,
        key=str.lower,
    )


