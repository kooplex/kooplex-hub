import logging
from dataclasses import dataclass

from django.db import transaction
from django.contrib.auth import get_user_model
from django.utils import timezone
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
    remove_project_member,
    add_project_member,
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
from .storage import (
    remove_project_storage,
)
from container.models import Container
from container.services.live import (
    broadcast_container_changed,
)
from container.services.runtime_control import (
    request_stop_automatically,
)

logger = logging.getLogger(__name__)
User = get_user_model()

MAX_OPERATION_ERROR_LENGTH = 4000


def _format_operation_error(error):
    return (
        f"{error.__class__.__name__}: {error}"
    )[:MAX_OPERATION_ERROR_LENGTH]



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
            state=Project.State.PREPARING,
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


def _require_project_creator(
    *,
    project,
    actor,
):
    binding = (
        UserProjectBinding.objects
        .filter(
            project=project,
            user=actor,
            role=(
                UserProjectBinding
                .Role
                .CREATOR
            ),
        )
        .first()
    )

    if binding is None:
        raise PermissionDenied(
            "Only the project creator may "
            "delete the project."
        )

    return binding


def _delete_unmounted_project(
    *,
    project_id,
    archive,
):
    project = (
        Project.objects
        .filter(pk=project_id)
        .first()
    )

    if project is None:
        return ProjectMembershipActionResult(
            project_id=project_id,
            action="deleted",
        )

    if project.containerbindings.exists():
        raise ValidationError(
            "The project is still mounted in "
            "one or more environments."
        )

    user_ids = tuple(
        project.userbindings.values_list(
            "user_id",
            flat=True,
        )
    )

    #
    # External filesystem operation:
    # deliberately outside a DB transaction.
    #
    remove_project_storage(
        project=project,
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


def delete_project(
    *,
    project,
    actor,
    archive=True,
):
    _require_project_creator(
        project=project,
        actor=actor,
    )

    return _delete_unmounted_project(
        project_id=project.pk,
        archive=archive,
    )


def request_forced_project_delete(
    *,
    project,
    actor,
    archive=True,
):
    from project.tasks import (
        continue_project_delete,
    )

    _require_project_creator(
        project=project,
        actor=actor,
    )

    with transaction.atomic():
        project = (
            Project.objects
            .select_for_update()
            .get(pk=project.pk)
        )

        if project.state == Project.State.DELETING:
            raise ValidationError(
                "Project deletion is already "
                "in progress."
            )

        if project.state not in {
            Project.State.READY,
            Project.State.PROVISION_FAILED,
            Project.State.DELETE_FAILED,
        }:
            raise ValidationError(
                "Project cannot be deleted "
                "from its current state."
            )

        project.state = (
            Project.State.DELETING
        )
        project.deletion_requested_at = (
            timezone.now()
        )
        project.last_operation_error = ""
        project.last_operation_failed_at = None

        project.save(
            update_fields=[
                "state",
                "deletion_requested_at",
                "last_operation_error",
                "last_operation_failed_at",
            ]
        )

        project_id = project.pk

        user_ids = tuple(
            project.userbindings.values_list(
                "user_id",
                flat=True,
            )
        )

        transaction.on_commit(
            lambda: continue_project_delete(
                project_id,
                archive,
            )
        )

        transaction.on_commit(
            lambda: broadcast_project_changed(
                project_id=project_id,
                user_ids=user_ids,
                reason=(
                    "project.deletion.started"
                ),
            )
        )

    return ProjectMembershipActionResult(
        project_id=project_id,
        action="deleting",
    )


def mark_project_delete_failed(
    *,
    project_id,
    error,
):
    updated = (
        Project.objects
        .filter(
            pk=project_id,
            state=Project.State.DELETING,
        )
        .update(
            state=(
                Project.State.DELETE_FAILED
            ),
            last_operation_error=(
                _format_operation_error(
                    error
                )
            ),
            last_operation_failed_at=(
                timezone.now()
            ),
        )
    )

    return updated == 1


def progress_project_delete(
    *,
    project_id,
    archive,
):
    project = (
        Project.objects
        .filter(pk=project_id)
        .first()
    )

    #
    # Already deleted = idempotent success.
    #
    if project is None:
        return True

    if project.state != Project.State.DELETING:
        return True

    bindings = list(
        project.containerbindings
        .select_related(
            "container__user",
        )
    )

    pending = False

    for binding in bindings:
        container = binding.container

        if (
            container.state
            == Container.State.NOTPRESENT
        ):
            continue

        if (
            container.state
            == Container.State.STOPPING
        ):
            pending = True
            continue

        notification = {
            "level": "warning",
            "message": (
                f"Environment "
                f"'{container.name}' "
                "is being stopped because "
                f"project '{project.name}' "
                "is being deleted."
            ),
        }

        request_stop_automatically(
            container_id=container.pk,
            reason=(
                "project.deletion"
            ),
            notification=notification,
        )

        pending = True

    if pending:
        return False

    #
    # Every attached environment currently
    # reports NOTPRESENT.
    #
    return finalize_project_delete(
        project_id=project_id,
        archive=archive,
    )


def finalize_project_delete(
    *,
    project_id,
    archive,
):
    project = (
        Project.objects
        .filter(
            pk=project_id,
            state=Project.State.DELETING,
        )
        .first()
    )

    if project is None:
        return True

    #
    # Final cheap check before touching
    # external storage.
    #
    attached_container_ids = tuple(
        project.containerbindings
        .values_list(
            "container_id",
            flat=True,
        )
    )

    if (
        Container.objects
        .filter(
            pk__in=attached_container_ids,
        )
        .exclude(
            state=Container.State.NOTPRESENT
        )
        .exists()
    ):
        return False

    #
    # No attached workload can now be newly
    # started because Project.state == DELETING.
    #
    remove_project_storage(
        project=project,
        archive=archive,
    )

    with transaction.atomic():
        project = (
            Project.objects
            .select_for_update()
            .get(pk=project_id)
        )

        if project.state != Project.State.DELETING:
            return True

        bindings = list(
            project.containerbindings
            .select_for_update()
            .select_related(
                "container",
            )
        )

        container_ids = [
            binding.container_id
            for binding in bindings
        ]

        #
        # Lock the Container rows too.
        # request_start()/request_restart()
        # use the same row locks.
        #
        containers = list(
            Container.objects
            .select_for_update()
            .filter(
                pk__in=container_ids
            )
        )

        if any(
            container.state
            != Container.State.NOTPRESENT
            for container in containers
        ):
            return False

        user_ids = tuple(
            project.userbindings.values_list(
                "user_id",
                flat=True,
            )
        )

        affected_containers = tuple(
            (
                container.pk,
                container.user_id,
            )
            for container in containers
        )

        #
        # Explicit, although Project.delete()
        # would cascade these too.
        #
        project.containerbindings.all().delete()

        project.delete()

        def notify_after_delete():
            broadcast_project_list_changed(
                user_ids=user_ids,
                reason="project.deleted",
            )

            for (
                container_id,
                user_id,
            ) in affected_containers:
                broadcast_container_changed(
                    container_id=container_id,
                    user_id=user_id,
                    reason=(
                        "project.mount.removed"
                    ),
                )

        transaction.on_commit(
            notify_after_delete
        )

    return True





