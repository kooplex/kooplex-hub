from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.db import transaction

from ..models import UserCourseBinding
from hub.services.groups import (
    add_user_to_group,
    remove_user_from_group,
)


ROLE_STUDENT = "student"
ROLE_TEACHER = "teacher"

COURSE_MEMBER_ROLE_CHOICES = (
    (ROLE_STUDENT, "Student"),
    (ROLE_TEACHER, "Teacher"),
)

def get_assignable_member_role_choices():
    return (
        {
            "value": "student",
            "label": "Student",
        },
        {
            "value": "teacher",
            "label": "Teacher",
        },
    )


@dataclass(frozen=True)
class CourseMemberSelection:
    user: object
    role: str

    @property
    def user_id(self):
        return self.user.pk

    @property
    def is_teacher(self):
        return self.role == ROLE_TEACHER


def validate_course_member_selections(
    *,
    selections,
    excluded_user_ids=(),
):
    excluded_user_ids = set(excluded_user_ids)
    seen = set()
    validated = []

    for selection in selections:
        if selection.user_id in excluded_user_ids:
            continue

        if selection.user_id in seen:
            raise ValidationError(
                "A user may only occur once in a course."
            )

        if selection.role not in {
            ROLE_STUDENT,
            ROLE_TEACHER,
        }:
            raise ValidationError(
                f"Invalid course role for {selection.user}."
            )

        seen.add(selection.user_id)
        validated.append(selection)

    return tuple(validated)


@transaction.atomic
def create_course_members(
    *,
    course,
    owner,
    members,
):
    selections = validate_course_member_selections(
        selections=members,
        excluded_user_ids={owner.pk},
    )

    created = []

    for selection in selections:
        binding = UserCourseBinding.objects.create(
            course=course,
            user=selection.user,
            is_teacher=selection.is_teacher,
        )
        created.append(binding)

    return tuple(created)


def course_group_for_role(*, course, is_teacher):
    return (
        course.group_teachers
        if is_teacher
        else course.group_students
    )


@transaction.atomic
def add_course_member(
    *,
    course,
    user,
    is_teacher,
):
    group = course_group_for_role(
        course=course,
        is_teacher=is_teacher,
    )

    if group is None:
        raise RuntimeError(
            "Course infrastructure is not provisioned."
        )

    binding, created = (
        UserCourseBinding.objects.get_or_create(
            course=course,
            user=user,
            defaults={
                "is_teacher": is_teacher,
            },
        )
    )

    if not created:
        if binding.is_teacher != is_teacher:
            raise ValueError(
                "User already belongs to the course "
                "with a different role."
            )

        return binding

    add_user_to_group(
        user=user,
        group=group,
    )

    return binding


@transaction.atomic
def change_course_member_role(
    *,
    binding,
    is_teacher,
):
    if binding.is_teacher == is_teacher:
        return binding

    old_group = course_group_for_role(
        course=binding.course,
        is_teacher=binding.is_teacher,
    )

    new_group = course_group_for_role(
        course=binding.course,
        is_teacher=is_teacher,
    )

    remove_user_from_group(
        user=binding.user,
        group=old_group,
    )

    add_user_to_group(
        user=binding.user,
        group=new_group,
    )

    binding.is_teacher = is_teacher
    binding.save(
        update_fields=["is_teacher"]
    )

    return binding


@transaction.atomic
def remove_course_member(*, binding):
    group = course_group_for_role(
        course=binding.course,
        is_teacher=binding.is_teacher,
    )

    remove_user_from_group(
        user=binding.user,
        group=group,
    )

    binding.delete()



