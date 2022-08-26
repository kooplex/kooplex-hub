import os
import logging

from django.db import models
from django.contrib.auth.models import User
from django.template.defaulttags import register

from container.models import Image


logger = logging.getLogger(__name__)


from education.models import Course, UserCourseBinding

class CourseGroup(models.Model):
    name = models.CharField(max_length = 64, null = False, unique = True)
    description = models.TextField(max_length = 512, blank = True)
    course = models.ForeignKey(Course, null = True, default = None, on_delete = models.CASCADE)

    class Meta:
        unique_together = [['name', 'course']]

    def __str__(self):
        return f'{self.name} ({self.description})'

    def students(self):
        return [ b.usercoursebinding.user for b in UserCourseGroupBinding.objects.filter(group = self) ]


class UserCourseGroupBinding(models.Model):
    usercoursebinding = models.OneToOneField(UserCourseBinding, null = False, on_delete = models.CASCADE)
    group = models.ForeignKey(CourseGroup, null = False, on_delete = models.CASCADE)



