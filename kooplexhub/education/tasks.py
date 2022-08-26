from celery import shared_task
from celery.utils.log import get_task_logger

from django.contrib.auth.models import User

from education.models import Course, UserCourseBinding
from education.models import Assignment, UserAssignmentBinding
from education.filesystem import *
from hub.models import Group

from hub.lib import mkdir, archivedir, extracttarbal
from hub.lib import grantaccess_user
from hub.lib import grantaccess_group

logger = get_task_logger(__name__)


@shared_task()
def assignment_handout(assignment_id):
    a = Assignment.objects.get(id = assignment_id)
    logger.info(f"handing out assignment {a.name} of course {a.course}")
    for sb in a.course.studentbindings:
        b, created = UserAssignmentBinding.objects.get_or_create(assignment = a, user = sb.user)
        if not created:
            logger.warning(f"student {sb.user} has already received assignment {a.name} in course {a.course.name}")
        b.handout()


@shared_task()
def assignment_collect(assignment_id):
    a = Assignment.objects.get(id = assignment_id)
    logger.info(f"collecting assignment {a.name} of course {a.course}")
    for b in UserAssignmentBinding.objects.filter(assignment = a, state = UserAssignmentBinding.ST_WORKINPROGRESS):
        b.collect(False)


def callback(uab_id, new_state):
    cnt = UserAssignmentBinding.objects.filter(id = uab_id).update(state = new_state)
    logger.info(f"callback {uab_id} -> {new_state} {cnt}")

@shared_task()
def task_periodic(vmi):
    pass
