import logging
from dataclasses import dataclass

from django.db import transaction
from django.contrib.auth import get_user_model
from django.core.exceptions import (
    ValidationError,
    PermissionDenied,
)

from ..models import (
    Project,
    UserProjectBinding,
)
from .members import (
    create_project_members,
    MembershipChanges,
)
from .names import (
    validate_project_name_for_creator,
)
from .mounts import (
    update_project_mounts
)

logger = logging.getLogger(__name__)
User = get_user_model()


@dataclass(frozen=True)
class ProjectCreationResult:
    project: object
    environment: object | None
    membership_changes: MembershipChanges
    mount_changes: object | None


@dataclass(frozen=True)
class ProjectMembershipActionResult:
    project_id: int
    action: str


class ProjectCreationService:
    @classmethod
    @transaction.atomic
    def create(
        cls,
        *,
        owner,
        name,
        scope,
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

        normalized_name = (
            validate_project_name_for_creator(
                creator=locked_owner,
                name=name,
            )
        )

        project = Project.objects.create(
            name=name,
            scope=scope,
            description=description,
            preferred_image=preferred_image,
        )

        UserProjectBinding.objects.create(
            project=project,
            user=locked_owner,
            role=UserProjectBinding.Role.CREATOR,
        )

        membership_changes = create_project_members(
            project=project,
            owner=locked_owner,
            members=members,
        )

        mount_changes = update_project_mounts(
            project=project,
            actor=owner,
            mounts=mounts,
        )

        environment = None

        if create_environment:
            environment = cls._create_environment(
                project=project,
                owner=locked_owner,
                image=preferred_image,
                mounts=mounts,
            )

        return ProjectCreationResult(
            project=project,
            environment=environment,
            membership_changes=membership_changes,
            mount_changes=mount_changes,
        )


    @staticmethod
    def _create_environment(
        *,
        project,
        owner,
        image,
        mounts,
    ):
        raise NotImplementedError


@transaction.atomic
def join_project(
    *,
    project,
    actor,
):
    if not Project.objects.joinable_by(
        actor
    ).filter(pk=project.pk).exists():
        raise ValidationError(
            "This project is not available to join."
        )

    binding, created = (
        UserProjectBinding.objects
        .get_or_create(
            project=project,
            user=actor,
            defaults={
                "role": (
                    UserProjectBinding
                    .Role
                    .COLLABORATOR
                ),
            },
        )
    )

    if not created:
        raise ValidationError(
            "You are already a member of this project."
        )

    return binding


@transaction.atomic
def leave_project(
    *,
    project,
    actor,
):
    binding = (
        UserProjectBinding.objects
        .select_for_update()
        .filter(
            project=project,
            user=actor,
        )
        .first()
    )

    if binding is None:
        raise PermissionDenied(
            "You are not a member of this project."
        )

    if binding.role == UserProjectBinding.Role.CREATOR:
        raise PermissionDenied(
            "The project creator cannot leave the project."
        )

    project_id = project.pk
    binding.delete()

    return ProjectMembershipActionResult(
        project_id=project_id,
        action="left",
    )


@transaction.atomic
def delete_project(
    *,
    project,
    actor,
):
    creator_binding = (
        UserProjectBinding.objects
        .select_for_update()
        .filter(
            project=project,
            user=actor,
            role=UserProjectBinding.Role.CREATOR,
        )
        .first()
    )

    if creator_binding is None:
        raise PermissionDenied(
            "Only the project creator may delete the project."
        )

    project_id = project.pk
    project.delete()

    return ProjectMembershipActionResult(
        project_id=project_id,
        action="deleted",
    )


