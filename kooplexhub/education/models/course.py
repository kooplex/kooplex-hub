import os
import logging

from django.db import models
from django.contrib.auth.models import User
from django.template.defaulttags import register

from container.models import Image


logger = logging.getLogger(__name__)


class Course(models.Model):
    name = models.CharField(max_length = 64, null = False, unique = True)
    folder = models.CharField(max_length = 64, null = False, unique = True)
    description = models.TextField(max_length = 512, blank = True)
    image = models.ForeignKey(Image, null = True, on_delete = models.CASCADE)
    teacher_can_delete_foreign_assignment = models.BooleanField(default = False)

    def __str__(self):
        return f'{self.name} ({self.folder})'

    @property
    def groups(self):
        from ..models import Group
        return Group.objects.filter(course = self)

    @register.filter
    def csv_groups(self):
        return ', '.join(map(lambda x: x.name, self.groups))

    @property
    def coursecodes(self):
        return CourseCode.objects.filter(course = self)

    @register.filter
    def csv_coursecodes(self):
        return ', '.join(map(lambda x: x.courseid, self.coursecodes))

    @property
    def teacherbindings(self):
        return UserCourseBinding.objects.filter(course = self, is_teacher = True)

    def teachers(self):
        return ", ".join([ f"{ucb.user.first_name} {ucb.user.last_name}" for ucb in self.teacherbindings ])

    def is_teacher(self, user):
        try:
            return UserCourseBinding.objects.get(course = self, user = user).is_teacher
        except UserCourseBinding.DoesNotExist:
            return False

    @property
    def studentbindings(self):
        return UserCourseBinding.objects.filter(course = self, is_teacher = False)

    @property
    def assignments(self):
        from .assignment import Assignment
        return Assignment.objects.filter(course = self) #FIXME: is_active

    @register.filter
    def csv_assignments(self):
        return ', '.join(map(lambda x: x.name, self.assignments))

    def dir_assignmentcandidate(self):
        from kooplexhub.lib import get_assignment_prepare_subfolders
        return get_assignment_prepare_subfolders(self)


    @staticmethod
    def get_usercourse(course_id, user):
        return UserCourseBinding.objects.get(user = user, course_id = course_id).course


class UserCourseBinding(models.Model):
    user = models.ForeignKey(User, null = False, on_delete = models.CASCADE)
    course = models.ForeignKey(Course, null = False, on_delete = models.CASCADE)
    is_teacher = models.BooleanField(default = False)

    class Meta:
        unique_together = [['user', 'course']]

    @property
    def assignments(self):
        return []
        from .assignment import Assignment
        for a in Assignment.objects.filter(course = self.course):
            yield a

    def coursecontainerbindings(self):
        from ..models import CourseContainerBinding
        return CourseContainerBinding.objects.filter(course = self.course, container__user = self.user)


class CourseCode(models.Model):
    courseid = models.CharField(max_length = 30, null = False, unique = True)
    course = models.ForeignKey(Course, null = True, default = None, on_delete = models.CASCADE)

    class Meta:
        ordering = [ 'courseid' ]

    def __str__(self):
        return f'{self.courseid}'


class UserCourseCodeBinding(models.Model):
    user = models.ForeignKey(User, null = False, on_delete = models.CASCADE)
    coursecode = models.ForeignKey(CourseCode, null = False, on_delete = models.CASCADE)
    is_teacher = models.BooleanField(default = False)


    @property
    def course(self):
        return self.coursecode.course
