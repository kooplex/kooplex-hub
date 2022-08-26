import os
import re
import logging
import json
import datetime

from django.db import models
from django.contrib.auth.models import User
from django.template.defaulttags import register
from django_celery_beat.models import ClockedSchedule, PeriodicTask

from hub.lib import dirname
from hub.models import Group
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
    def safename(self):
        return re.sub(r'[\.\ ]', '', self.name)

    @property
    def snapshot(self):
        return os.path.join(dirname.course_assignment_snapshot(self.course), 'assignment-snapshot-%s.%d.tar.gz' % (self.safename, self.created_at.timestamp()))

class UserAssignmentBinding(models.Model):
    ST_QUEUED = 'qed'
    ST_WORKINPROGRESS = 'wip'
    ST_SUBMITTED = 'sub'
    ST_COLLECTED = 'col'
    ST_CORRECTED = 'cor'
    ST_READY = 'rdy'
    ST_TRANSITIONAL = 'tsk'
    ST_LOOKUP = {
        ST_QUEUED: 'Waiting for handout',
        ST_WORKINPROGRESS: 'Working on assignment',
        ST_SUBMITTED: 'Submitted, waiting for corrections',
        ST_COLLECTED: 'Collected, waiting for corrections',
        ST_CORRECTED: 'Assignment is being corrected',
        ST_READY: 'Assignment is corrected',
        ST_TRANSITIONAL: 'An asynchronous task is scheduled now',
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
    task_correct = models.ForeignKey(PeriodicTask, null = True, blank = True, on_delete = models.SET_NULL, related_name = 'u_extract2correct')
    task_finalize = models.ForeignKey(PeriodicTask, null = True, blank = True, on_delete = models.SET_NULL, related_name = 'u_finalize')

    class Meta:
        unique_together = [['user', 'assignment']]
        ordering = [ 'assignment__name' ]


    def __str__(self):
        return f'{self.assignment.name} ({self.assignment.course.name})'

    @register.filter
    def state_long(self):
        return ST_LOOKUP[self.state] 

#FIXME: ALWAYS CHECK STATE!!!!
    def handout(self):
        if self.id is None:
            self.save()
        now = datetime.datetime.now()
        group = Group.objects.get(name = self.assignment.course.cleanname, grouptype = Group.TP_COURSE)
        schedule_now = ClockedSchedule.objects.create(clocked_time = now)
        self.task_handout = PeriodicTask.objects.create(
            name = f"handout_{self.assignment.folder}_{self.user.username}-{now}",
            task = "kooplexhub.tasks.extract_tar",
            clocked = schedule_now,
            one_off = True,
            kwargs = json.dumps({
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
            })
        )
        self.state = self.ST_TRANSITIONAL
        self.save()

    def collect(self, submit = True):
        assert self.state == UserAssignmentBinding.ST_WORKINPROGRESS, "State mismatch"
        now = datetime.datetime.now()
        self.submitted_at = now
        self.submit_count += 1
        if self.task_collect:
            self.task_collect.clocked.clocked_time = now
            self.task_collect.clocked.save()
        else:
            schedule_now = ClockedSchedule.objects.create(clocked_time = now)
            self.task_collect = PeriodicTask.objects.create(
                name = f"snapshot_{self.id}",
                task = "kooplexhub.tasks.create_tar",
                clocked = schedule_now,
                one_off = True,
        #FIXME: QUOTA CHECK HANDLE IT
                kwargs = json.dumps({
                    'folder': assignment_workdir(self),
                    'tarbal': assignment_collection(self),
                    'callback': {
                        'function': "education.tasks.callback",
                        'kwargs': {
                            'uab_id': self.id,
                            'new_state': UserAssignmentBinding.ST_SUBMITTED if submit else UserAssignmentBinding.ST_COLLECTED,
                        }
                    }
                })
            )
        self.state = self.ST_TRANSITIONAL
        self.save()

    def extract2correct(self):
        assert self.state in [ UserAssignmentBinding.ST_SUBMITTED, UserAssignmentBinding.ST_COLLECTED ], "State mismatch"
        now = datetime.datetime.now()
        if self.task_correct:
            self.task_correct.clocked.clocked_time = now
            self.task_correct.clocked.save()
        else:
            schedule_now = ClockedSchedule.objects.create(clocked_time = now)
            self.task_correct = PeriodicTask.objects.create(
                name = f"extract_{self.id}",
                task = "kooplexhub.tasks.extract_tar",
                clocked = schedule_now,
                one_off = True,
                kwargs = json.dumps({
                    'folder': assignment_correct_dir(self),
                    'tarbal': assignment_collection(self),
                    'users_rw': [ b.user.id for b in self.assignment.course.teacherbindings ],
                    'callback': {
                        'function': "education.tasks.callback",
                        'kwargs': {
                            'uab_id': self.id,
                            'new_state': UserAssignmentBinding.ST_CORRECTED,
                        }
                    }
                })
            )
        self.state = self.ST_TRANSITIONAL
        self.save()

    def finalize(self, user, score, message):
        assert self.state == UserAssignmentBinding.ST_CORRECTED, "State mismatch"
        now = datetime.datetime.now()
        self.corrected_at = now
        if self.task_finalize:
            self.task_finalize.clocked.clocked_time = now
            self.task_finalize.clocked.save()
        else:
            schedule_now = ClockedSchedule.objects.create(clocked_time = now)
            self.task_finalize = PeriodicTask.objects.create(
                name = f"finalize_{self.id}",
                task = "kooplexhub.tasks.create_tar",
                clocked = schedule_now,
                one_off = True,
        #FIXME: feedback csak student kérésére lesz kicsomagolva
                kwargs = json.dumps({
                    'binding_id': self.id,
                    'folder': assignment_correct_dir(self), 
                    'tarbal': assignment_feedback(self),
                    'callback': {
                        'function': "education.tasks.callback",
                        'kwargs': {
                            'uab_id': self.id,
                            'new_state': UserAssignmentBinding.ST_READY,
                        }
                    }
                })
            )
        self.correction_count += 1
        self.corrector = user
        self.feedback_text = message
        self.score = score
        self.state = self.ST_TRANSITIONAL
        self.save()

    def reassign(self):
        self.state = UserAssignmentBinding.ST_WORKINPROGRESS
        self.save()
