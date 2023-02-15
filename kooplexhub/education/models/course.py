import os
import logging

from django.db import models
from django.contrib.auth.models import User
from django.template.defaulttags import register

from kooplexhub.lib import my_alphanumeric_validator
from container.models import Image
from hub.models import Group


logger = logging.getLogger(__name__)


class Course(models.Model):
    class Meta:
       app_label = 'education'

    name = models.CharField(max_length = 64, null = False, unique = True)
    folder = models.CharField(max_length = 64, null = False, unique = True)
    description = models.TextField(max_length = 512, blank = True)
    image = models.ForeignKey(Image, null = True, on_delete = models.CASCADE)
    teacher_can_delete_foreign_assignment = models.BooleanField(default = False)
    os_group = models.ForeignKey(Group, null = True, on_delete = models.CASCADE, default = None)


    def __str__(self):
        return f'{self.name} ({self.folder})'

    @property
    def search(self):
        return f"{self.name} {self.folder} {self.description} {self.teachers()}".upper()

    @property
    def groups(self):
        from education.models import CourseGroup
        students = set([ b.user for b in self.studentbindings ])
        groups = dict([ (g, g.students()) for g in CourseGroup.objects.filter(course = self) ])
        for g in groups.values():
            students.difference_update(g)
        if len(students):
            groups[None] = students
        return groups

    @register.filter
    def csv_groups(self):
        return ', '.join(map(lambda x: f'{"ungrouped" if x[0] is None else x[0].name} ({len(x[1])} students)', self.groups.items()))

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
        from . import Assignment
        return Assignment.objects.filter(course = self) #FIXME: is_active

    @register.filter
    def csv_assignments(self):
        return ', '.join(map(lambda x: x.name, self.assignments))

    def dir_assignmentcandidate(self):
        from education.filesystem import get_assignment_prepare_subfolders
        return get_assignment_prepare_subfolders(self)


    @staticmethod
    def get_usercourse(course_id, user):
        return UserCourseBinding.objects.get(user = user, course_id = course_id).course

    def is_user_authorized(self, user):
        try:
            UserCourseBinding.objects.get(user = user, course = self)
            return True
        except UserCourseBinding.DoesNotExist:
            return False



class UserCourseBinding(models.Model):
    user = models.ForeignKey(User, null = False, on_delete = models.CASCADE)
    course = models.ForeignKey(Course, null = False, on_delete = models.CASCADE)
    is_teacher = models.BooleanField(default = False)

    class Meta:
        unique_together = [['user', 'course']]

    def __str__(self):
        if self.is_teacher:
            return "teacher {} of course {}".format(self.user, self.course)
        else:
            return "student {} in course {}".format(self.user, self.course)

    #@property
    #def assignments(self):
    #    return []
    #    from education.models import Assignment
    #    for a in Assignment.objects.filter(course = self.course):
    #        yield a

    def coursecontainerbindings(self):
        from . import CourseContainerBinding
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
