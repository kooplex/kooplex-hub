from dataclasses import dataclass

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone

from kooplexhub.lib.libbase import standardize_str

from ..models import (
    Course,
    UserCourseBinding,
)
from ..services.provisioning import (
    provision_course_infrastructure,
    provision_course_filesystem,
)
from ..services.members import (
    add_course_member,
)
from .members import create_course_members
from .mounts import update_course_mounts
from .environments import create_default_course_environment


User = get_user_model()


@dataclass(frozen=True)
class CourseCreationResult:
    course: object
    environment: object | None
    member_bindings: tuple
    mount_changes: object


class CourseCreationService:

    @classmethod
    @transaction.atomic
    def create(
        cls,
        *,
        owner,
        name,
        description,
        preferred_image,
        members,
        mounts,
        create_environment,
    ):
        locked_owner = (
            User.objects
            .select_for_update()
            .get(pk=owner.pk)
        )

        if not locked_owner.profile.can_createcourse:
            raise PermissionDenied(
                "You are not allowed to create courses."
            )

        folder = cls._make_folder(name)

        infrastructure = (
            provision_course_infrastructure(
                folder=folder,
            )
        )

        course = Course.objects.create(
            name=name,
            description=description,
            preferred_image=preferred_image,
            folder=folder,
            group_students=(
                infrastructure.student_group
            ),
            group_teachers=(
                infrastructure.teacher_group
            ),
        )

        provision_course_filesystem(
            course=course,
        )

        # Creator is always a teacher.
        add_course_member(
            course=course,
            user=locked_owner,
            is_teacher=True,
        )

        membership_changes = (
            create_course_members(
                course=course,
                owner=locked_owner,
                members=members,
            )
        )

        mount_changes = update_course_mounts(
            course=course,
            mounts=mounts,
        )

        environment = None

        if create_environment:
            environment = create_default_course_environment(
                course=course,
                user=locked_owner,
            )

        return CourseCreationResult(
            course=course,
            environment=environment,
            member_bindings=membership_changes,
            mount_changes=mount_changes,
        )

    @staticmethod
    def _make_folder(name):
        base = (
            f"{timezone.localdate().year}-"
            f"{standardize_str(name)}"
        )

        folder = base
        suffix = 2

        while Course.objects.filter(folder=folder).exists():
            folder = f"{base}-{suffix}"
            suffix += 1

        return folder



