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
    inspect_course_filesystem,
    mark_course_provisioning_complete,
    mark_course_provisioning_failed,
    CourseProvisioningError,
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
    def _create_definition(
        cls,
        *,
        owner,
        name,
        description,
        preferred_image,
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

        course = Course.objects.create(
            name=name,
            description=description,
            preferred_image=preferred_image,
            folder=folder,
             provisioning_state=(
                Course.ProvisioningState.PREPARING
            ),
        )

        return course, locked_owner


    @classmethod
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
        course, owner = cls._create_definition(
            owner=owner,
            name=name,
            description=description,
            preferred_image=preferred_image,
        )
    
        try:
            infrastructure = (
                provision_course_infrastructure(
                    folder=course.folder,
                )
            )
    
            course.group_students = (
                infrastructure.student_group
            )
            course.group_teachers = (
                infrastructure.teacher_group
            )
    
            course.save(
                update_fields=[
                    "group_students",
                    "group_teachers",
                ]
            )
    
            provision_course_filesystem(
                course=course,
            )
    
            filesystem_status = (
                inspect_course_filesystem(
                    course=course,
                )
            )
    
            if not filesystem_status.ready:
                raise CourseProvisioningError(
                    "Course filesystem is incomplete; "
                    "missing: "
                    + ", ".join(
                        filesystem_status.missing
                    )
                )
    
            # A ready course must at least be usable
            # by its creator.
            add_course_member(
                course=course,
                user=owner,
                is_teacher=True,
            )
    
        except Exception as error:
            mark_course_provisioning_failed(
                course_id=course.pk,
                error=error,
            )
            raise
    
        mark_course_provisioning_complete(
            course_id=course.pk,
        )
    
        course.refresh_from_db()
    
        #
        # Optional course configuration follows.
        # These are not part of core infrastructure
        # provisioning.
        #
        membership_changes = (
            create_course_members(
                course=course,
                owner=owner,
                members=members,
            )
        )
    
        mount_changes = update_course_mounts(
            course=course,
            mounts=mounts,
        )
    
        environment = None
    
        if create_environment:
            environment = (
                create_default_course_environment(
                    course=course,
                    user=owner,
                )
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



