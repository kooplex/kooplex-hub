import os
import logging

from django.db import models
from django.db.models.signals import pre_save, post_save, pre_delete, post_delete
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.template.defaulttags import register

from .course import Course, UserCourseBinding

from kooplex.settings import KOOPLEX
from kooplex.lib import standardize_str

logger = logging.getLogger(__name__)

class Assignment(models.Model):
    course = models.ForeignKey(Course, null = False)
    flag = models.CharField(max_length = 32, null = True)
    name = models.CharField(max_length = 32, null = False)
    creator = models.ForeignKey(User, null = False)
    description = models.TextField(max_length = 500, blank = True)
    folder = models.CharField(max_length = 32, null = False)
    created_at = models.DateTimeField(auto_now_add = True)
    valid_from = models.DateTimeField(auto_now_add = True)
    expires_at = models.DateTimeField(null = True)
    can_studentsubmit = models.BooleanField(default = True)

    @property
    def safename(self):
        return standardize_str(self.name)


ST_LOOKUP = {
    'wip': 'Working on assignment',
    'sub': 'Submitted, waiting for corrections',
    'col': 'Collected, waiting for corrections',
    'cor': 'Assignment is being corrected',
    'rdy': 'Assignment is corrected',
}

class UserAssignmentBinding(models.Model):
    ST_WORKINPROGRESS = 'wip'
    ST_SUBMITTED = 'sub'
    ST_COLLECTED = 'col'
    ST_CORRECTING = 'cor'
    ST_FEEDBACK = 'rdy'
    STATE_LIST = [ ST_WORKINPROGRESS, ST_SUBMITTED, ST_COLLECTED, ST_CORRECTING, ST_FEEDBACK ]

    user = models.ForeignKey(User, null = False)
    assignment = models.ForeignKey(Assignment, null = False)
    received_at = models.DateTimeField(auto_now_add = True)
    state = models.CharField(max_length = 16, choices = [ (x, ST_LOOKUP[x]) for x in STATE_LIST ], default = ST_WORKINPROGRESS)
    submitted_at = models.DateTimeField(null = True)
    corrector = models.ForeignKey(User, null = True, related_name = 'corrector')
    corrected_at = models.DateTimeField(null = True)

    @property
    def state_long(self):
        return ST_LOOKUP[self.state] 

    @property
    def submittable(self):
        if not self.assignment.can_studentsubmit:
            return False
        return self.state in [ self.ST_WORKINPROGRESS, self.ST_SUBMITTED ]


@receiver(post_save, sender = Assignment)
def snapshot_assignment(sender, instance, created, **kwargs):
    from kooplex.lib.filesystem import snapshot_assignment
    from .course import UserCourseBinding
    if created:
        snapshot_assignment(instance)
        for binding in UserCourseBinding.objects.filter(course = instance.course, flag = instance.flag, is_teacher = False):
            # FIXME: if not within interval, schedule it!
            UserAssignmentBinding.objects.create(user = binding.user, assignment = instance)

@receiver(pre_delete, sender = Assignment)
def garbage_assignmentsnapshot(sender, instance, **kwargs):
    from kooplex.lib.filesystem import garbagedir_assignmentsnapshot
    garbagedir_assignmentsnapshot(instance)


@receiver(post_save, sender = UserCourseBinding)
def add_userassignmentbinding(sender, instance, created, **kwargs):
    if created and not instance.is_teacher:
        for a in instance.assignments:
            UserAssignmentBinding.objects.create(user = instance.user, assignment = a)


@receiver(post_save, sender = UserAssignmentBinding)
def copy_userassignment(sender, instance, created, **kwargs):
    from kooplex.lib.filesystem import cp_assignmentsnapshot, cp_userassignment, cp_userassignment2correct, manageacl_feedback, Dirname
    from .container import Container
    if created:
        cp_assignmentsnapshot(instance)
    elif instance.state in [ UserAssignmentBinding.ST_SUBMITTED, UserAssignmentBinding.ST_COLLECTED ]:
        cp_userassignment(instance)
        mapping = "+:%s:%s" % (Dirname.assignmentcollectdir(instance, in_hub = False), instance.assignment.safename)
        Container.manage_report_mount(user = instance.user, project =instance.assignment.course.project, mapping = mapping)
    elif instance.state == UserAssignmentBinding.ST_CORRECTING:
        cp_userassignment2correct(instance)
        mapping = "+:%s:%s" % (Dirname.assignmentcorrectdir(instance, in_hub = False), instance.assignment.safename)
        Container.manage_report_mount(user = instance.corrector, project =instance.assignment.course.project, mapping = mapping)
    elif instance.state == UserAssignmentBinding.ST_FEEDBACK:
        manageacl_feedback(instance)
        mapping = "+:%s:%s" % (Dirname.assignmentcorrectdir(instance, in_hub = False), instance.assignment.safename)
        Container.manage_report_mount(user = instance.user, project =instance.assignment.course.project, mapping = mapping)

