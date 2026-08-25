from dataclasses import dataclass

from django.db import transaction

from ..models import VolumeCourseBinding


@dataclass(frozen=True)
class CourseMountChanges:
    added: tuple
    removed: tuple

    @property
    def changed(self):
        return bool(self.added or self.removed)


@transaction.atomic
def update_course_mounts(
    *,
    course,
    mounts,
):
    desired = {
        volume.pk: volume
        for volume in mounts
    }

    existing_bindings = list(
        VolumeCourseBinding.objects
        .filter(course=course)
        .select_related("volume")
    )

    existing = {
        binding.volume_id: binding
        for binding in existing_bindings
    }

    added = []
    removed = []

    for volume_id, volume in desired.items():
        if volume_id in existing:
            continue

        added.append(
            VolumeCourseBinding.objects.create(
                course=course,
                volume=volume,
            )
        )

    for volume_id, binding in existing.items():
        if volume_id in desired:
            continue

        removed.append(binding)
        binding.delete()

    return CourseMountChanges(
        added=tuple(added),
        removed=tuple(removed),
    )
