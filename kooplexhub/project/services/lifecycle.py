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
    make_project_subpath,
    validate_project_name_for_creator,
)
from .mounts import (
    update_project_mounts
)
from .live import (
    broadcast_project_changed,
    broadcast_project_list_changed,
    project_member_user_ids,
)
from .provisioning import (
    mark_project_provisioning_complete,
    mark_project_provisioning_failed,
    provision_project_infrastructure,
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
    @staticmethod
    @transaction.atomic
    def _create_definition(
        *,
        owner,
        name,
        scope,
        description,
        preferred_image,
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

        subpath = make_project_subpath(
            creator=locked_owner,
            normalized_name=normalized_name,
        )

        project = Project.objects.create(
            name=normalized_name,
            scope=scope,
            description=description,
            preferred_image=preferred_image,
            subpath=subpath,
            provisioning_state=(
                Project.ProvisioningState.PREPARING
            ),
        )

        UserProjectBinding.objects.create(
            project=project,
            user=locked_owner,
            role=(
                UserProjectBinding.Role.CREATOR
            ),
        )

        project_id = project.pk
        owner_id = locked_owner.pk

        transaction.on_commit(
            lambda: (
                broadcast_project_list_changed(
                    user_ids=(owner_id,),
                    reason="project.created",
                )
            )
        )

        return project

    @classmethod
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
        project = cls._create_definition(
            owner=owner,
            name=name,
            scope=scope,
            description=description,
            preferred_image=preferred_image,
        )

        try:
            provision_project_infrastructure(
                project=project,
                owner=owner,
            )

            project.refresh_from_db()

            membership_changes = (
                create_project_members(
                    project=project,
                    owner=owner,
                    members=members,
                )
            )

            mount_changes = (
                update_project_mounts(
                    project=project,
                    actor=owner,
                    mounts=mounts,
                )
            )

            completed = (
                mark_project_provisioning_complete(
                    project_id=project.pk,
                )
            )

            if not completed:
                raise RuntimeError(
                    "Project provisioning state "
                    "changed unexpectedly."
                )

        except Exception as error:
            mark_project_provisioning_failed(
                project_id=project.pk,
                error=error,
            )

            user_ids = (
                project_member_user_ids(
                    project
                )
            )

            broadcast_project_changed(
                project_id=project.pk,
                user_ids=user_ids,
                reason=(
                    "project.provisioning.failed"
                ),
            )

            broadcast_project_list_changed(
                user_ids=user_ids,
                reason=(
                    "project.provisioning.failed"
                ),
            )

            raise

        project.refresh_from_db()

        user_ids = project_member_user_ids(
            project
        )

        broadcast_project_changed(
            project_id=project.pk,
            user_ids=user_ids,
            reason=(
                "project.provisioning.completed"
            ),
        )

        # Newly-added collaborators did not have
        # this Project in their grid before.
        broadcast_project_list_changed(
            user_ids=user_ids,
            reason="project.ready",
        )

        environment = None

        if create_environment:
            environment = (
                cls._create_environment(
                    project=project,
                    owner=owner,
                    image=preferred_image,
                    mounts=mounts,
                )
            )

        return ProjectCreationResult(
            project=project,
            environment=environment,
            membership_changes=(
                membership_changes
            ),
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
        # I would leave this separate for this
        # pass. The smoke test below creates its
        # own Container explicitly.
        raise NotImplementedError


@transaction.atomic
def join_project(
    *,
    project,
    actor,
):
    project = (
        Project.objects
        .select_for_update()
        .get(pk=project.pk)
    )

    if not (
        Project.objects
        .joinable_by(actor)
        .filter(pk=project.pk)
        .exists()
    ):
        raise ValidationError(
            "This project is not available "
            "to join."
        )

    binding = add_project_member(
        project=project,
        user=actor,
        role=(
            UserProjectBinding
            .Role
            .COLLABORATOR
        ),
    )

    project_id = project.pk
    actor_id = actor.pk

    member_user_ids = tuple(
        project.userbindings.values_list(
            "user_id",
            flat=True,
        )
    )

    transaction.on_commit(
        lambda: broadcast_project_changed(
            project_id=project_id,
            user_ids=member_user_ids,
            reason="project.member.joined",
        )
    )

    transaction.on_commit(
        lambda: broadcast_project_list_changed(
            user_ids=(actor_id,),
            reason="project.joined",
        )
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
        .select_related(
            "project__group",
            "user",
        )
        .filter(
            project=project,
            user=actor,
        )
        .first()
    )

    if binding is None:
        raise PermissionDenied(
            "You are not a member "
            "of this project."
        )

    if (
        binding.role
        == UserProjectBinding.Role.CREATOR
    ):
        raise PermissionDenied(
            "The project creator cannot "
            "leave the project."
        )

    project_id = project.pk
    actor_id = actor.pk

    member_user_ids = tuple(
        project.userbindings.values_list(
            "user_id",
            flat=True,
        )
    )

    remove_project_member(
        binding=binding,
    )

    remaining_user_ids = tuple(
        user_id
        for user_id in member_user_ids
        if user_id != actor_id
    )

    transaction.on_commit(
        lambda: broadcast_project_changed(
            project_id=project_id,
            user_ids=remaining_user_ids,
            reason="project.member.left",
        )
    )

    transaction.on_commit(
        lambda: broadcast_project_list_changed(
            user_ids=(actor_id,),
            reason="project.left",
        )
    )

    return ProjectMembershipActionResult(
        project_id=project_id,
        action="left",
    )


def delete_project(
    *,
    project,
    actor,
    archive=True,
):
    creator_binding = (
        UserProjectBinding.objects
        .filter(
            project=project,
            user=actor,
            role=(
                UserProjectBinding.Role.CREATOR
            ),
        )
        .first()
    )

    if creator_binding is None:
        raise PermissionDenied(
            "Only the project creator may "
            "delete the project."
        )

    if project.containerbindings.exists():
        raise ValidationError(
            "The project is still mounted in "
            "one or more environments."
        )

    project_id = project.pk

    user_ids = tuple(
        project.userbindings.values_list(
            "user_id",
            flat=True,
        )
    )

    # External filesystem operation OUTSIDE
    # the database transaction.
    remove_project_workdir(
        project,
        archive=archive,
    )

    with transaction.atomic():
        locked = (
            Project.objects
            .select_for_update()
            .get(pk=project_id)
        )

        if locked.containerbindings.exists():
            raise ValidationError(
                "The project became attached "
                "to an environment while it "
                "was being removed."
            )

        locked.delete()

        transaction.on_commit(
            lambda: (
                broadcast_project_list_changed(
                    user_ids=user_ids,
                    reason="project.deleted",
                )
            )
        )

    return ProjectMembershipActionResult(
        project_id=project_id,
        action="deleted",
    )



