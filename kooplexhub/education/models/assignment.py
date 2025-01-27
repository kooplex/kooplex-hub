import os
import re
import logging
import json

from django.db import models
from django.contrib.auth.models import User
from django.template.defaulttags import register


from django.utils import timezone

from kooplexhub.lib.libbase import standardize_str

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
    created_at = models.DateTimeField(editable=False,null=True,auto_now_add=True)
    valid_from = models.DateTimeField(blank=True,null=True)
    expires_at = models.DateTimeField(blank=True,null=True)
    remove_collected = models.BooleanField(default = False,null=True)
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
    def n_queued(self):
        if not self.id: return None
        students = self.course.students
        missing = len(students)-len(UserAssignmentBinding.objects.filter(assignment=self, user__in=students))
        return len(UserAssignmentBinding.objects.filter(assignment=self, state=UserAssignmentBinding.ST_QUEUED)) + missing

    @property
    def n_workinprogress(self):
        return len(UserAssignmentBinding.objects.filter(assignment=self, state=UserAssignmentBinding.ST_WORKINPROGRESS))

    @property
    def n_collected(self):
        return len(UserAssignmentBinding.objects.filter(assignment=self, state__in=[UserAssignmentBinding.ST_COLLECTED, UserAssignmentBinding.ST_READY]))

    def snapshot(self):
        from ..tasks import assignment_create
        assignment_create(self)

    def handout(self):
        now=timezone.now()
        if self.valid_from and now<self.valid_from:
            logging.warning(f"Early assignment handout {self.name} / {self.course.name}")
        elif self.expires_at and self.expires_at<now:
            logging.warning(f"Late assignment handout {self.name} / {self.course.name}")
        for s in self.course.students:
            b, created = UserAssignmentBinding.objects.get_or_create(assignment = self, user_id = s.id)
            try:
                b.handout()
            except Exception as e:
                flag = 'new' if created else 'old'
                logger.error(f"Cannot handout assignment {self.name} / {self.course.name} -> {b} {flag}. -- {e}")

    def collect(self):
        now=timezone.now()
        if self.expires_at and now<self.expires_at:
            logging.warning(f"Early assignment collection {self.name} / {self.course.name}")
        for s in self.course.students:
            b, created = UserAssignmentBinding.objects.get_or_create(assignment = self, user_id = s.id)
            try:
                b.collect()
            except Exception as e:
                logger.error(f"Cannot collect assignment {self.name} / {self.course.name} -> {b}. -- {e}")


class UserAssignmentBinding(models.Model):
    ST_QUEUED = 'qed'
    ST_EXTRACTING = 'ext'
    ST_WORKINPROGRESS = 'wip'
    ST_COMPRESSING = 'snap'
    ST_COLLECTED = 'col'
    ST_READY = 'rdy'
    ST_LOOKUP = {
        ST_QUEUED: 'Waiting for handout',
        ST_EXTRACTING: 'Extracting tar in workdir',
        ST_WORKINPROGRESS: 'Working on assignment',
        ST_COMPRESSING: 'Snapshot workdir, and extract in correct folder',
        ST_COLLECTED: 'Submitted or collected, waiting for corrections',
        ST_READY: 'Assignment is corrected',
    }

    user = models.ForeignKey(User, null = False, on_delete = models.CASCADE)
    assignment = models.ForeignKey(Assignment, null = False, on_delete = models.CASCADE)
    state = models.CharField(max_length = 16, choices = ST_LOOKUP.items(), default = ST_QUEUED)
    corrector = models.ForeignKey(User, null = True, related_name = 'corrector', on_delete = models.CASCADE, blank = True)
    last_received_at = models.DateTimeField(editable=False,null=True)
    last_submitted_at = models.DateTimeField(editable=False,null=True)
    last_corrected_at = models.DateTimeField(editable=False,null=True)
    score = models.FloatField(null = True, default = None, blank = True)
    feedback_text = models.TextField(null = True, default = None, blank = True)
    submit_count = models.IntegerField(default = 0, null = False)
    correction_count = models.IntegerField(default = 0, null = False)

    class Meta:
        unique_together = [['user', 'assignment']]
        ordering = [ 'assignment__name' ]


    def __str__(self):
        return f'{self.assignment.name} ({self.assignment.course.name})'

    @register.filter
    def state_long(self):
        return ST_LOOKUP[self.state] 


    def handout(self):
        from ..tasks import assignment_handout
        if self.state != UserAssignmentBinding.ST_QUEUED:
            #logger.debug(f"Cannot handout assignment {self.assignment.name} / {self.assignment.course.name} -> {self.user} -- already handed out")
            return
        self.last_received_at = timezone.now()
        self.state = self.ST_EXTRACTING
        self.save()
        assignment_handout(self)


    def collect(self):
        from ..tasks import assignment_collect
        if self.state != UserAssignmentBinding.ST_WORKINPROGRESS:
            #logger.debug(f"Cannot collect assignment {self.assignment.name} / {self.assignment.course.name} -> {self.user}")
            return
        self.last_submitted_at = timezone.now()
        self.submit_count += 1
        self.state = self.ST_COMPRESSING
        self.save()
        assignment_collect(self)


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
