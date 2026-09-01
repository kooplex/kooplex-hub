import uuid

from django.db import transaction
from django.utils.text import slugify

from ..models import Container
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


def _container_label(*, user, name):
    base = slugify(
        f"{user.username}-{name}"
    ) or "container"

    return (
        f"{base[:180]}-"
        f"{uuid.uuid4().hex[:8]}"
    )


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
            user=user,
            image=image,
            name=name,
            label=_container_label(
                user=user,
                name=name,
            ),
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


