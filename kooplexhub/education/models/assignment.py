import os
import re
import logging
import json

from django.db import models
from django.contrib.auth.models import User
from django.template.defaulttags import register
from django_celery_beat.models import ClockedSchedule, PeriodicTask
from django.utils import timezone

from kooplexhub.lib.libbase import standardize_str

from hub.lib import dirname
from hub.models import Group, Task
from . import Course, UserCourseBinding
from education.filesystem import *

logger = logging.getLogger(__name__)


class Assignment(models.Model):
    name = models.CharField(max_length = 32, null = False)
    course = models.ForeignKey(Course, null = False, on_delete = models.CASCADE)
    creator = models.ForeignKey(User, null = False, on_delete = models.CASCADE)
    description = models.TextField(max_length = 500)
    folder = models.CharField(max_length = 32, null = False)
    created_at = models.DateTimeField(auto_now_add = True)
    task_snapshot = models.ForeignKey(PeriodicTask, null = True, blank = True, on_delete = models.SET_NULL, related_name = 'snapshot')
    task_handout = models.ForeignKey(PeriodicTask, null = True, blank = True, on_delete = models.SET_NULL, related_name = 'handout')
    task_collect = models.ForeignKey(PeriodicTask, null = True, blank = True, on_delete = models.SET_NULL, related_name = 'collect')
    remove_collected = models.BooleanField(default = False)
    max_size = models.IntegerField(default = None, null = True, blank = True) 
    filename = models.CharField(max_length = 256, null = False, unique = True)

    class Meta:
        unique_together = [['course', 'folder']]

    def __str__(self):
        return f"Assignment {self.name} (course {self.course.name}@{self.creator.username})"

    @property
    def search(self):
        return f"{self.name} {self.description} {self.folder} {self.course.name}".upper()

    @property
    def _safename(self):
        return standardize_str(f'{self.course.name}-{self.folder}')

    @property
    def _task_snapshot(self):
        self.filename = os.path.join(course_assignment_snapshot(self.course), f'assignment-snapshot-{self._safename}.{time.time()}.tar.gz')
        return Task(
            name = f"Create assignment snapshot: {self.name}/{self.course.name}",
            task = "kooplexhub.tasks.create_tar",
            kwargs = {
                'folder': assignment_source(self),
                'tarbal': self.filename,
            }
        )

    def _task_handout(self, when):
        return Task(
            when = when,
            name = f"Handout: {self.name}/{self.course.name}",
            task = "education.tasks.assignment_handout",
            kwargs = {
                'course_id': self.course.id,
                'assignment_folder': self.folder,
            }
        )

    def _task_collect(self, when):
        return Task(
            when = when,
            name = f"Collect: {self.name}/{self.course.name}",
            task = "education.tasks.assignment_collect",
            kwargs = {
                'course_id': self.course.id,
                'assignment_folder': self.folder,
            }
        )

    #FIXME: ide kell bevezetni a taskok létrehozását, a form könnyebb lesz


class UserAssignmentBinding(models.Model):
    ST_QUEUED = 'qed'
    ST_EXTRACTING = 'ext'
    ST_WORKINPROGRESS = 'wip'
    ST_COMPRESSING = 'snap'
    ST_SUBMITTED = 'sub'
    ST_COLLECTED = 'col'
    ST_READY = 'rdy'
    ST_LOOKUP = {
        ST_QUEUED: 'Waiting for handout',
        ST_EXTRACTING: 'Extracting tar in workdir',
        ST_WORKINPROGRESS: 'Working on assignment',
        ST_COMPRESSING: 'Snapshot workdir, and extract in correct folder',
        ST_SUBMITTED: 'Submitted, waiting for corrections',
        ST_COLLECTED: 'Collected, waiting for corrections',
        ST_READY: 'Assignment is corrected',
    }

    user = models.ForeignKey(User, null = False, on_delete = models.CASCADE)
    assignment = models.ForeignKey(Assignment, null = False, on_delete = models.CASCADE)
    received_at = models.DateTimeField(null = True, default = None, blank = True)
    state = models.CharField(max_length = 16, choices = ST_LOOKUP.items(), default = ST_QUEUED)
    submitted_at = models.DateTimeField(null = True, default = None, blank = True)
    corrector = models.ForeignKey(User, null = True, related_name = 'corrector', on_delete = models.CASCADE, blank = True)
    corrected_at = models.DateTimeField(null = True, default = None, blank = True)
    score = models.FloatField(null = True, default = None, blank = True)
    feedback_text = models.TextField(null = True, default = None, blank = True)
    submit_count = models.IntegerField(default = 0, null = False)
    correction_count = models.IntegerField(default = 0, null = False)
    task_handout = models.ForeignKey(PeriodicTask, null = True, blank = True, on_delete = models.SET_NULL, related_name = 'u_handout')
    task_collect = models.ForeignKey(PeriodicTask, null = True, blank = True, on_delete = models.SET_NULL, related_name = 'u_collect')
    #task_finalize = models.ForeignKey(PeriodicTask, null = True, blank = True, on_delete = models.SET_NULL, related_name = 'u_finalize')

    class Meta:
        unique_together = [['user', 'assignment']]
        ordering = [ 'assignment__name' ]


    def __str__(self):
        return f'{self.assignment.name} ({self.assignment.course.name})'

    @register.filter
    def state_long(self):
        return ST_LOOKUP[self.state] 

    def handout(self):
        if self.task_handout:
            return
        assert self.state == UserAssignmentBinding.ST_QUEUED, "State mismatch"
        group = self.assignment.course.os_group
        self.task_handout = Task(
            name = f"handout {self.assignment.name}/{self.assignment.course.name} to {self.user.username}",
            task = "kooplexhub.tasks.extract_tar",
            kwargs = {
                'folder': assignment_workdir(self),
                'tarbal': self.assignment.filename,
                'users_rw': [ self.user.id ],
                'users_ro': [ teacherbinding.user.id for teacherbinding in self.assignment.course.teacherbindings ],
                'recursive': True,
                'callback': {
                    'function': "education.tasks.callback",
                    'kwargs': {
                        'uab_id': self.id,
                        'new_state': UserAssignmentBinding.ST_WORKINPROGRESS,
                    }
                }
            }
        )
        self.state = self.ST_EXTRACTING
        self.task_handout.save()
        self.save()

    def collect(self, submit = True):
        assert self.state == UserAssignmentBinding.ST_WORKINPROGRESS, "State mismatch"
        now = timezone.now()
        self.submitted_at = now
        self.submit_count += 1
        if self.task_collect:
            self.task_collect.clocked.clocked_time = now
            self.task_collect.clocked.save()
        else:
            self.task_collect = Task(
                name = f"Collect assignment {self.assignment.name}/{self.assignment.course.name} from {self.user.username}",
                task = "education.tasks.submission",
                kwargs = {
                    'userassignmentbinding_id': self.id,
                    'new_state': UserAssignmentBinding.ST_SUBMITTED if submit else UserAssignmentBinding.ST_COLLECTED,
                }
            )
            self.task_collect.save()
        self.state = self.ST_COMPRESSING
        self.save()


    def finalize(self, user, score, message):
        assert self.state == UserAssignmentBinding.ST_CORRECTED, "State mismatch"
        now = timezone.now()
        self.corrected_at = now
        self.correction_count += 1
        self.corrector = user
        self.feedback_text = message
        self.score = score
        self.state = self.ST_READY
        self.save()

    def reassign(self):
        #FIXME: Ha le van törölve, mert ZH típusu, akkor ennek nincs értelme
        self.state = UserAssignmentBinding.ST_WORKINPROGRESS
        self.save()
