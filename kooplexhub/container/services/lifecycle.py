from django.db import transaction

from ..models import Container
from .labels import generate_container_label
from .image_catalog import (
    ImageCatalogService,
)
from .live import (
    broadcast_container_list_changed,
    broadcast_container_changed,
)
from .runtime_control import (
    ContainerActionError,
    request_stop_automatically,
)
from .mounts import (
    apply_container_mounts,
)

from project.models import Project
from education.models import Course
from volume.models import Volume


class ContainerLifecycleError(RuntimeError):
    pass


def _resolve_selected_items(
    *,
    user,
    project_ids,
    course_ids,
    volume_ids,
):
    project_ids = set(project_ids)
    course_ids = set(course_ids)
    volume_ids = set(volume_ids)

    projects = list(
        Project.objects
        .attachable_by(user)
        .filter(pk__in=project_ids)
        .order_by("name")
    )

    courses = list(
        Course.objects
        .attachable_by(user)
        .filter(pk__in=course_ids)
        .order_by("name")
    )

    volumes = list(
        Volume.objects
        .attachable_by(user)
        .filter(pk__in=volume_ids)
        .order_by("folder")
    )

    if {
        project.pk
        for project in projects
    } != project_ids:
        raise ContainerLifecycleError(
            "One or more selected projects "
            "are no longer available."
        )

    if {
        course.pk
        for course in courses
    } != course_ids:
        raise ContainerLifecycleError(
            "One or more selected courses "
            "are no longer available."
        )

    if {
        volume.pk
        for volume in volumes
    } != volume_ids:
        raise ContainerLifecycleError(
            "One or more selected volumes "
            "are no longer available."
        )

    return projects, courses, volumes


def create_container(
    *,
    user,
    name,
    image,
    project_ids=(),
    course_ids=(),
    volume_ids=(),
    requested_cpu_m=None,
    requested_memory_mib=None,
    requested_gpu=None,
):
    image = (
        ImageCatalogService
        .available_for_user(user)
        .filter(pk=image.pk)
        .first()
    )

    if image is None:
        raise ContainerLifecycleError(
            "The selected image is no longer "
            "available."
        )

    create_kwargs = {
        "user": user,
        "image": image,
        "name": name,
        "label": generate_container_label(
            user=user,
            name=name,
        ),
    }

    if requested_cpu_m is not None:
        create_kwargs[
            "requested_cpu_m"
        ] = requested_cpu_m
    
    if requested_memory_mib is not None:
        create_kwargs[
            "requested_memory_mib"
        ] = requested_memory_mib
    
    if requested_gpu is not None:
        create_kwargs[
            "requested_gpu"
        ] = requested_gpu

    projects, courses, volumes = (
        _resolve_selected_items(
            user=user,
            project_ids=project_ids,
            course_ids=course_ids,
            volume_ids=volume_ids,
        )
    )

    with transaction.atomic():
        container = Container.objects.create(
            **create_kwargs,
        )

        apply_container_mounts(
            container=container,
            projects=projects,
            courses=courses,
            volumes=volumes,
        )

        container_id = container.pk
        user_id = user.pk

        transaction.on_commit(
            lambda: (
                broadcast_container_list_changed(
                    user_id=user_id,
                    reason="container.created",
                )
            )
        )

    return container


def request_container_deletion(*, container, actor):
    """Persist deletion intent; a periodic reconciler completes it safely."""
    with transaction.atomic():
        current = Container.objects.select_for_update().get(
            pk=container.pk, user=actor,
        )
        if current.delete_requested:
            return False
        current.delete_requested = True
        current.require_running = False
        current.save(update_fields=["delete_requested", "require_running"])
        # Reconciler requests stop after this transaction commits.  It also
        # handles STARTING/STOPPING states and worker restarts.
    return True


def reconcile_pending_deletions():
    """Advance pending deletions; never bypass delete_container's guard."""
    from .runtime_control import _request_container_stop, ContainerActionError

    ids = list(Container.objects.filter(delete_requested=True)
               .values_list("pk", flat=True))
    for container_id in ids:
        try:
            container = Container.objects.get(pk=container_id)
            if not container.delete_requested:
                continue
            if container.state == Container.State.NOTPRESENT:
                delete_container(container=container)
            elif container.state in {
                Container.State.STARTING,
                Container.State.RUNNING,
                Container.State.NEED_RESTART,
                Container.State.ERROR,
            }:
                _request_container_stop(container_id=container_id)
            # STOPPING is already being handled by the runtime watcher.
        except Container.DoesNotExist:
            continue
        except (ContainerActionError, ContainerLifecycleError):
            # Another task may have advanced the state in the meantime.
            continue


def delete_container(
    *,
    container,
    actor=None,
):
    with transaction.atomic():
        container = (
            Container.objects
            .select_for_update()
            .get(pk=container.pk)
        )

        if (
            actor is not None
            and container.user_id
            != actor.pk
        ):
            raise ContainerLifecycleError(
                "You cannot delete this "
                "environment."
            )

        if (
            container.state
            != Container.State.NOTPRESENT
        ):
            raise ContainerLifecycleError(
                "A running or transitioning "
                "environment cannot be deleted."
            )

        container_id = container.pk
        user_id = container.user_id

        container.delete()

        transaction.on_commit(
            lambda: (
                broadcast_container_list_changed(
                    user_id=user_id,
                    reason="container.deleted",
                )
            )
        )

    return container_id


