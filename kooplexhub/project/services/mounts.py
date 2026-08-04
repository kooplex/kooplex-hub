from dataclasses import dataclass

from django.db import transaction

from volume.models import ProjectVolumeBinding


@dataclass(frozen=True)
class MountChanges:
    added: tuple
    removed: tuple

    @property
    def changed(self):
        return bool(
            self.added
            or self.removed
        )


@transaction.atomic
def update_project_mounts(
    *,
    project,
    actor,
    mounts,
):
    desired = {
        volume.pk: volume
        for volume in mounts
    }

    existing_bindings = list(
        ProjectVolumeBinding.objects
        .filter(project=project)
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

        binding = ProjectVolumeBinding.objects.create(
            project=project,
            volume=volume,
        )
        added.append(binding)

    for volume_id, binding in existing.items():
        if volume_id in desired:
            continue

        removed.append(binding)
        binding.delete()

    return MountChanges(
        added=tuple(added),
        removed=tuple(removed),
    )



def get_current_mount_ids(project):
    return set(
        project.volumebindings
        .values_list("volume_id", flat=True)
    )



