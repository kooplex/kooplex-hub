import os
import logging

from django.db import models
from django.db.models.signals import pre_save, post_save, pre_delete, post_delete
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.template.defaulttags import register

from .course import Course, UserCourseBinding

from kooplex.settings import KOOPLEX
from kooplex.lib import standardize_str, now

logger = logging.getLogger(__name__)

class Assignment(models.Model):
    course = models.ForeignKey(Course, null = False)
    flag = models.CharField(max_length = 32, null = True)
    name = models.CharField(max_length = 32, null = False)
    creator = models.ForeignKey(User, null = False)
    description = models.TextField(max_length = 500)
    folder = models.CharField(max_length = 32, null = False)
    created_at = models.DateTimeField(auto_now_add = True)
    valid_from = models.DateTimeField(null = False)
    expires_at = models.DateTimeField(null = True)
    can_studentsubmit = models.BooleanField(default = True)
    is_massassignment = models.BooleanField(default = True)

    def __str__(self):
        return "%s [%s/%s@%s]" % (self.name, self.course.courseid, self.flag, self.creator)

    @property
    def safename(self):
        return standardize_str(self.name)

    def list_students_bindable(self):
        students = []
        for usercoursebinding in UserCourseBinding.objects.filter(course = self.course, flag = self.flag, is_teacher = False):
            try:
                UserAssignmentBinding.objects.get(assignment = self, user = usercoursebinding.user)
            except UserAssignmentBinding.DoesNotExist:
                students.append(usercoursebinding.user)
        return students

    ST_SCHEDULED, ST_VALID, ST_EXPIRED = range(3)
    @property
    def state(self):
        timenow = now()
        dt = self.valid_from - timenow
        if dt.total_seconds() > 0:
            return self.ST_SCHEDULED
        if self.expires_at is None or (self.expires_at - timenow).total_seconds() >= 0:
            return self.ST_VALID
        else:
            return self.ST_EXPIRED

    @staticmethod
    def iter_valid():
        for a in Assignment.objects.filter(is_massassignment = True):
            if a.state == Assignment.ST_VALID:
                yield a

    def bind_students(self):
        student_list = self.list_students_bindable()
        for student in student_list:
            UserAssignmentBinding.objects.create(user = student, assignment = self, expires_at = self.expires_at)
            logger.info("handout %s -> %s" % (self, student))
        return student_list

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
    valid_from = models.DateTimeField(null = True)
    expires_at = models.DateTimeField(null = True)
    state = models.CharField(max_length = 16, choices = [ (x, ST_LOOKUP[x]) for x in STATE_LIST ], default = ST_WORKINPROGRESS)
    submitted_at = models.DateTimeField(null = True)
    corrector = models.ForeignKey(User, null = True, related_name = 'corrector')
    corrected_at = models.DateTimeField(null = True)

    def __str__(self):
        return "%s by %s" % (self.assignment, self.user)

    @property
    def state_long(self):
        return ST_LOOKUP[self.state] 

    @property
    def submittable(self):
        if not self.assignment.can_studentsubmit:
            return False
        return self.state in [ self.ST_WORKINPROGRESS, self.ST_SUBMITTED ]

    @staticmethod
    def iter_expired():
        timenow = now()
        for binding in UserAssignmentBinding.objects.filter(state = UserAssignmentBinding.ST_WORKINPROGRESS):
            if binding.expires_at is None:
                continue
            dt = timenow - binding.expires_at
            if dt.total_seconds() > 0:
                yield binding

    def do_collect(self):
        #FIXME: we may double check state and skip some bindings
        self.state = UserAssignmentBinding.ST_COLLECTED
        self.submitted_at = now()
        self.save()
        logger.info(self)


@receiver(post_save, sender = Assignment)
def snapshot_assignment(sender, instance, created, **kwargs):
    from kooplex.lib.filesystem import snapshot_assignment
    if created:
        snapshot_assignment(instance)
        if not instance.is_massassignment:
            return
        if instance.state == instance.ST_VALID:
            student_list = instance.bind_students()


@receiver(pre_delete, sender = Assignment)
def garbage_assignmentsnapshot(sender, instance, **kwargs):
    from kooplex.lib.filesystem import garbagedir_assignmentsnapshot
    garbagedir_assignmentsnapshot(instance)


@receiver(post_save, sender = UserCourseBinding)
def add_userassignmentbinding(sender, instance, created, **kwargs):
    if created and not instance.is_teacher:
        for a in instance.assignments:
            if a.state == a.ST_VALID:
                UserAssignmentBinding.objects.create(user = instance.user, assignment = a, expires_at = a.expires_at)


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
        mapping = "-:%s" % (instance.assignment.safename)
        Container.manage_report_mount(user = instance.corrector, project =instance.assignment.course.project, mapping = mapping)


