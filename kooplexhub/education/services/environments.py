from django.db import transaction

from container.models import Container
from volume.models import VolumeContainerBinding

from ..models import (
    CourseContainerBinding,
    VolumeCourseBinding,
)


class CourseEnvironmentCreationError(Exception):
    pass


def unique_generated_container_name(course, user):
    base_name = f"Generated for course {course.name}"
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
def create_default_course_environment(
    *,
    course,
    user,
):
    if course.preferred_image_id is None:
        raise CourseEnvironmentCreationError(
            "Select a preferred image before creating an environment."
        )

    container = Container.objects.create(
        user=user,
        name=unique_generated_container_name(
            course=course,
            user=user,
        ),
        image=course.preferred_image,
    )

    CourseContainerBinding.objects.create(
        course=course,
        container=container,
    )

    volume_ids = list(
        VolumeCourseBinding.objects
        .filter(course=course)
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
