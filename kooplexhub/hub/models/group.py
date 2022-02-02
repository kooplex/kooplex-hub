import logging

from django.db import models
from django.contrib.auth.models import User

logger = logging.getLogger(__name__)

class Group(models.Model):
    TP_PROJECT = 'project'
    TP_COURSE = 'course'
    TP_VOLUME = 'volume'
    TP_LOOKUP = {
        TP_PROJECT: 'projectgroup',
        TP_COURSE: 'coursegroup',
        TP_VOLUME: 'volumegroup'
    }

    groupid = models.IntegerField(null = False, unique = True, blank = False)
    name = models.CharField(max_length = 32, unique = True, null = False)
    grouptype = models.CharField(max_length = 16, choices = TP_LOOKUP.items(), default = TP_PROJECT)
    #description = models.TextField(null = True)

    def __str__(self):
        return "{} ({})".format(self.name, self.groupid)


class UserGroupBinding(models.Model):
    user = models.ForeignKey(User, null = False, on_delete = models.CASCADE)
    group = models.ForeignKey(Group, null = False, on_delete = models.CASCADE)

    def __str__(self):
        return "{} in {}".format(self.user, self.group)
