from django.db import transaction

from ..models import (
    ProjectContainerBinding,
)
from container.models import Container
from volume.models import (
    VolumeContainerBinding,
    ProjectVolumeBinding,
)


class ProjectEnvironmentCreationError(Exception):
    pass


def unique_generated_container_name(project, user):
    base_name = f"Generated for project {project.name}"
    name = base_name
    suffix = 2

    while Container.objects.filter(
        user=user,
        name=name,
    ).exists():
        name = f"{base_name} ({suffix})"
        suffix += 1

    return name


@transaction.atomic
def create_default_project_environment(
    *,
    project,
    user,
):
    if project.preferred_image_id is None:
        raise ProjectEnvironmentCreationError(
            "Select a preferred image before creating an environment."
        )

    container = Container.objects.create(
        user=user,
        name=unique_generated_container_name(
            project=project,
            user=user,
        ),
        image=project.preferred_image,
    )

    ProjectContainerBinding.objects.create(
        project=project,
        container=container,
    )

    volume_ids = list(
        ProjectVolumeBinding.objects
        .filter(project=project)
        .values_list("volume_id", flat=True)
    )

    VolumeContainerBinding.objects.bulk_create(
        [
            VolumeContainerBinding(
                container=container,
                volume_id=volume_id,
            )
            for volume_id in volume_ids
        ],
        ignore_conflicts=True,
    )

    return container
