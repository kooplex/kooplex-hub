from celery import shared_task
import logging

from django.contrib.auth.models import User

from education.models import Course, UserCourseBinding
from education.models import Assignment, UserAssignmentBinding
from education.filesystem import *
from hub.models import Group

from hub.lib import mkdir, archivedir, extracttarbal
from hub.lib import grantaccess_user
from hub.lib import grantaccess_group

logger = logging.getLogger(__name__)


@shared_task()
def assignment_handout(assignment_id):
    a = Assignment.objects.get(id = assignment_id)
    logger.info(f"handing out assignment {a.name} of course {a.course}")
    for sb in a.course.studentbindings:
        b, created = UserAssignmentBinding.objects.get_or_create(assignment = a, user = sb.user)
        if not created:
            logger.warning(f"student {sb.user} has already received assignment {a.name} in course {a.course.name}")


@shared_task()
def assignment_collect(assignment_id):
    a = Assignment.objects.get(id = assignment_id)
    logger.info(f"collecting assignment {a.name} of course {a.course}")
    bindings = UserAssignmentBinding.objects.filter(assignment = a, state = UserAssignmentBinding.ST_WORKINPROGRESS)
    bindings.update(state = UserAssignmentBinding.ST_COLLECTED)


