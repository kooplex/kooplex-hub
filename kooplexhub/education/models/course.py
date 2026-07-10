import os
import logging

from django.db import models
from django.db.models import Q
from django.core.validators import MinLengthValidator
from container.models import Image
from hub.models import Group
from django.contrib.auth import get_user_model

from education.fs import get_assignment_prepare_subfolders

User = get_user_model()


logger = logging.getLogger(__name__)


class CourseQuerySet(models.QuerySet):
    def bound_to(self, user, include_hidden=False):
        """
        Courses where the user has an explicit UserCourseBinding.
        """
        if not user.is_authenticated:
            return self.none()

        if user.is_superuser:
            return self

        return self.filter(
            userbindings__user=user,
        ).distinct()

    def student_for(self, user):
        """
        Courses where the user is a student.
        """
        if not user.is_authenticated:
            return self.none()

        if user.is_superuser:
            return self

        return self.filter(
            userbindings__user=user,
            userbindings__is_teacher=False,
        ).distinct()

    def teacher_for(self, user):
        """
        Courses where the user is a teacher.
        """
        if not user.is_authenticated:
            return self.none()

        if user.is_superuser:
            return self

        return self.filter(
            userbindings__user=user,
            userbindings__is_teacher=True,
        ).distinct()

    def member_of(self, user):
        """
        Courses where the user is either a student or a teacher.
        """
        return self.bound_to(user)

    def visible_to(self, user):
        """
        Courses the user may see.
        For now, this is the same as membership.
        """
        return self.member_of(user)

    def attachable_by(self, user):
        """
        Courses the user may mount into an environment.
        For now, any course membership allows mounting.
        """
        return self.member_of(user)

    def manageable_by(self, user):
        """
        Courses where the user has teacher privileges.
        """
        return self.teacher_for(user)

    def for_user(self, user):
        """
        Backwards-compatible alias.
        Prefer visible_to(), attachable_by(), manageable_by() in new code.
        """
        return self.visible_to(user)


class Course(models.Model):
    class Meta:
       app_label = 'education'

    name = models.CharField(
        max_length=64,
        unique=True,
        validators=[
            MinLengthValidator(
                3,
                message="Name must be at least 3 characters.",
            )
        ],
    )

    folder = models.CharField(
        max_length=64,
        unique=True,
    )

    description = models.TextField(
        max_length=512,
        blank=True,
        validators=[
            MinLengthValidator(
                5,
                message="Description must be at least 5 characters.",
            )
        ],
    )

    preferred_image = models.ForeignKey(
        Image,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    teacher_can_delete_foreign_assignment = models.BooleanField(
        default=False,
    )

    group_students = models.ForeignKey(
        Group,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        default=None,
        related_name="students",
        help_text="Filesystem/LDAP group used for student course storage access.",
    )

    group_teachers = models.ForeignKey(
        Group,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        default=None,
        related_name="teachers",
        help_text="Filesystem/LDAP group used for teacher course storage access.",
    )

    objects = CourseQuerySet.as_manager()

    def __str__(self):
        return f'{self.name} ({self.folder})'


    @property
    def search(self):
        return f"{self.name} {self.description}".upper()

#FIXME
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


#################


    @property
    def assignments(self):
        #FIXME relat
        from . import Assignment
        return Assignment.objects.filter(course = self)


    def dir_assignmentcandidate(self):
        return get_assignment_prepare_subfolders(self)

    @property
    def volumes(self):
        from . import VolumeCourseBinding
        return list(map(lambda o: o.volume, VolumeCourseBinding.objects.filter(course=self)))


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
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="coursebindings",
    )

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="userbindings",
    )

    is_teacher = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "course"],
                name="unique_user_course_binding",
            ),
        ]

        indexes = [
            models.Index(fields=["user", "is_teacher"]),
            models.Index(fields=["course", "is_teacher"]),
        ]

    def __str__(self):
        if self.is_teacher:
            return "teacher {} of course {}".format(self.user, self.course)
        else:
            return "student {} in course {}".format(self.user, self.course)

    def coursecontainerbindings(self):
        from . import CourseContainerBinding
        return CourseContainerBinding.objects.filter(course = self.course, container__user = self.user)

    def assignments_table(self):
        from ..tables import TableAssignment
        from . import UserAssignmentBinding
        return TableAssignment(UserAssignmentBinding.objects.filter(user=self.user, assignment__course=self.course))


