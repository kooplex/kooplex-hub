from celery import shared_task
from celery.utils.log import get_task_logger

from django.contrib.auth.models import User

from education.models import Course, UserCourseBinding
from education.models import Assignment, UserAssignmentBinding
from education.filesystem import *
from hub.models import Group

from hub.lib import archivedir, extracttarbal
from hub.lib import grantaccess_user
from hub.lib import grantaccess_group

logger = get_task_logger(__name__)


def callback(uab_id, new_state):
    cnt = UserAssignmentBinding.objects.filter(id = uab_id).update(state = new_state)
    logger.info(f"callback {uab_id} -> {new_state} {cnt}")


@shared_task()
def assignment_handout(course_id, assignment_folder):
    a = Assignment.objects.get(course__id = course_id, folder = assignment_folder)
    logger.info(f"handing out assignment {a.name} of course {a.course}")
    for sb in a.course.studentbindings:
        b, created = UserAssignmentBinding.objects.get_or_create(assignment = a, user = sb.user)
        try:
            b.handout()
        except Exception as e:
            flag = 'new' if created else 'old'
            logger.error(f"Cannot handout assignment {a.name} / {a.course.name} -> {b} {flag}. -- {e}")


@shared_task()
def assignment_collect(course_id, assignment_folder):
    a = Assignment.objects.get(course__id = course_id, folder = assignment_folder)
    logger.info(f"Collecting assignment {a.name} of course {a.course}")
    for b in UserAssignmentBinding.objects.filter(assignment = a, state = UserAssignmentBinding.ST_WORKINPROGRESS):
        try:
            b.collect(submit = False)
        except Exception as e:
            logger.error(f"Cannot collect assignment {a.name} / {a.course.name} <- {b}. -- {e}")


@shared_task()
def submission(userassignmentbinding_id, new_state):
    uab = UserAssignmentBinding.objects.get(id = userassignmentbinding_id)
    logger.debug(f"Submission {uab}")
    folder = assignment_workdir(uab)
    tarbal = assignment_collection(uab)
    # UJ
    group_teachers = Group.objects.get(name = f't-{uab.assignment.course.folder}').groupid 
    ##
    correct_folder = assignment_correct_dir(uab)
    archivedir(folder, tarbal, remove = uab.assignment.remove_collected)
    extracttarbal(tarbal, correct_folder)
    # for ucb in uab.assignment.course.teacherbindings:
    #     grantaccess_user(ucb.user, correct_folder, readonly = False, recursive = True, follow = False)
    ## UJ
    grantaccess_group(group_teachers, correct_folder, readonly = False)
    ##
    uab.state = new_state
    uab.save()
    logger.info(f"Submission finished {uab}")
