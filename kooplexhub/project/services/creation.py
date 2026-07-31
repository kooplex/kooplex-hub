import logging
from dataclasses import dataclass

from django.db import transaction
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from .members import (
    create_project_members,
    MembershipChanges,
)
from ..models import (
    Project,
    UserProjectBinding,
)
from .names import (
    validate_project_name_for_creator,
)

logger = logging.getLogger(__name__)
User = get_user_model()


@dataclass(frozen=True)
class ProjectCreationResult:
    project: object
    environment: object | None
    membership_changes: MembershipChanges
    mount_changes: object | None

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

        mount_changes = None #TODO

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
