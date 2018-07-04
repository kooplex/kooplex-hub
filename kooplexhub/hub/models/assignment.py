import os
import logging

from django.db import models
from django.db.models.signals import pre_save, post_save, pre_delete, post_delete
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.template.defaulttags import register

from .course import Course

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


class UserAssignmentBinding(models.Model):
    ST_WORKINPROGRESS = {
        'short': 'wip', 
        'long': 'Working on assignment',
    }
    ST_SUBMITTED = {
        'short': 'sub', 
        'long': 'Submitted, waiting for corrections',
    }
    ST_RESUBMITTED = {
        'short': 'res', 
        'long': 'Resubmitted before corrections',
    }
    ST_CORRECTING = {
        'short': 'cor', 
        'long': 'Assignment is being corrected',
    }
    ST_FEEDBACK = {
        'short': 'rdy', 
        'long': 'Assignment is corrected',
    }
    STATE_LIST = [ST_WORKINPROGRESS, ST_SUBMITTED, ST_CORRECTING, ST_FEEDBACK]

    user = models.ForeignKey(User, null = False)
    assignment = models.ForeignKey(Assignment, null = False)
    version = models.IntegerField(null = False)
    state = models.CharField(max_length = 16, choices = [ (x['short'], x['long']) for x in STATE_LIST ])
    submitted_at = models.DateTimeField(null = True)
    corrected_at = models.DateTimeField(null = True)


