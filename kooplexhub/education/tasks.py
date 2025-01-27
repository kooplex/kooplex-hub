import logging

from channels.layers import get_channel_layer
from django_huey import task, periodic_task, get_queue
from huey import crontab
from asgiref.sync import async_to_sync

from django.contrib.auth.models import User

from education.models import Course, UserCourseBinding
from education.models import Assignment, UserAssignmentBinding
from education.filesystem import *
from hub.models import Group

from hub.lib import archivedir, extracttarbal
from hub.lib import grantaccess_user
from hub.lib import grantaccess_group
from django.utils import timezone
import time


logger = logging.getLogger(__name__)

qc=get_queue('course')

@qc.periodic_task(crontab(minute='*'))
def check_handout_and_collect():
    now=timezone.now()
    for a in Assignment.objects.filter(valid_from__lt=now).exclude(expires_at__lt=now):
        a.handout()
    for a in Assignment.objects.filter(expires_at__lt=now):
        a.collect()


@task(queue = 'course')
def assignment_create(assignment):
    assignment.filename = os.path.join(course_assignment_snapshot(assignment.course), f'assignment-snapshot-{assignment._safename}.{time.time()}.tar.gz')
    folder=assignment_source(assignment)
    archivedir(folder, assignment.filename, remove=False)


@task(queue = 'course')
def assignment_handout(userassignmentbinding):
    folder=assignment_workdir(userassignmentbinding)
    extracttarbal(userassignmentbinding.assignment.filename, folder)
    gid=userassignmentbinding.assignment.course.group_teachers.groupid
    grantaccess_group(gid, folder, readonly=True, recursive=True)
    userassignmentbinding.state=userassignmentbinding.ST_WORKINPROGRESS
    userassignmentbinding.save()


@task(queue = 'course')
def assignment_collect(userassignmentbinding):
    folder=assignment_workdir(userassignmentbinding)
    tarbal=assignment_collection(userassignmentbinding)
    gid=userassignmentbinding.assignment.course.group_teachers.groupid
    correct_folder=assignment_correct_dir(userassignmentbinding)
    archivedir(folder, tarbal, remove=userassignmentbinding.assignment.remove_collected)
    extracttarbal(tarbal, correct_folder)
    grantaccess_group(gid, correct_folder, readonly=False)
    userassignmentbinding.state=userassignmentbinding.ST_COLLECTED
    userassignmentbinding.save()

