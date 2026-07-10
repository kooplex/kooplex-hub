from dataclasses import dataclass
from typing import Iterable

from django.db import models, transaction

from project.models import ProjectContainerBinding
from education.models import CourseContainerBinding
from volume.models import VolumeContainerBinding

@dataclass(frozen=True)
class MountBindingSpec:
    name: str
    plural_name: str
    binding_model: type[models.Model]
    item_fk: str
    label_attr: str = "name"

    @property
    def item_id_field(self):
        return f"{self.item_fk}_id"


@dataclass
class MountSyncResult:
    name: str
    plural_name: str
    added: list
    removed: list

    @property
    def changed(self):
        return bool(self.added or self.removed)


def sync_container_mounts(container, desired_items: Iterable, spec: MountBindingSpec):
    """
    Synchronize one mount type for one container.

    Example:
      desired_items = queryset/list of Project objects
      spec.item_fk = "project"
      spec.binding_model = ProjectContainerBinding
    """

    desired_items = list(desired_items)
    desired_by_id = {
        item.pk: item
        for item in desired_items
        if item.pk is not None
    }

    desired_ids = set(desired_by_id)

    existing_bindings = list(
        spec.binding_model.objects
        .filter(container=container)
        .select_related(spec.item_fk)
    )

    existing_by_id = {
        getattr(binding, spec.item_id_field): binding
        for binding in existing_bindings
    }

    existing_ids = set(existing_by_id)

    ids_to_add = desired_ids - existing_ids
    ids_to_remove = existing_ids - desired_ids

    added_items = [
        desired_by_id[item_id]
        for item_id in ids_to_add
        if item_id in desired_by_id
    ]

    removed_items = [
        getattr(existing_by_id[item_id], spec.item_fk)
        for item_id in ids_to_remove
        if item_id in existing_by_id
    ]

    with transaction.atomic():
        spec.binding_model.objects.bulk_create(
            [
                spec.binding_model(
                    container=container,
                    **{spec.item_id_field: item_id},
                )
                for item_id in ids_to_add
            ],
            ignore_conflicts=True,
        )

        if ids_to_remove:
            spec.binding_model.objects.filter(
                container=container,
                **{f"{spec.item_id_field}__in": ids_to_remove},
            ).delete()

    return MountSyncResult(
        name=spec.name,
        plural_name=spec.plural_name,
        added=added_items,
        removed=removed_items,
    )


PROJECT_MOUNT_SPEC = MountBindingSpec(
    name="project",
    plural_name="projects",
    binding_model=ProjectContainerBinding,
    item_fk="project",
    label_attr="name",
)

COURSE_MOUNT_SPEC = MountBindingSpec(
    name="course",
    plural_name="courses",
    binding_model=CourseContainerBinding,
    item_fk="course",
    label_attr="name",
)

VOLUME_MOUNT_SPEC = MountBindingSpec(
    name="storage volume",
    plural_name="storage volumes",
    binding_model=VolumeContainerBinding,
    item_fk="volume",
    label_attr="folder",
)

def apply_container_mounts(container, projects, courses, volumes):
    return {
        "projects": sync_container_mounts(
            container=container,
            desired_items=projects,
            spec=PROJECT_MOUNT_SPEC,
        ),
        "courses": sync_container_mounts(
            container=container,
            desired_items=courses,
            spec=COURSE_MOUNT_SPEC,
        ),
        "volumes": sync_container_mounts(
            container=container,
            desired_items=volumes,
            spec=VOLUME_MOUNT_SPEC,
        ),
    }

def mount_change_message(results):
    parts = []

    for result in results.values():
        if result.added:
            parts.append(
                "Added "
                + result.plural_name
                + ": "
                + ", ".join(_label(item, result) for item in result.added)
            )

        if result.removed:
            parts.append(
                "Removed "
                + result.plural_name
                + ": "
                + ", ".join(_label(item, result) for item in result.removed)
            )

    return "; ".join(parts) or "Mounts unchanged."


def _label(item, result):
    return str(getattr(item, result.name, None) or item)


def get_current_mount_ids(container, spec):
    return set(
        spec.binding_model.objects
        .filter(container=container)
        .values_list(spec.item_id_field, flat=True)
    )


def get_current_container_mount_ids(container):
    return {
        "project_ids": get_current_mount_ids(container, PROJECT_MOUNT_SPEC),
        "course_ids": get_current_mount_ids(container, COURSE_MOUNT_SPEC),
        "volume_ids": get_current_mount_ids(container, VOLUME_MOUNT_SPEC),
    }


def get_current_mount_items(container, spec):
    return [
        getattr(binding, spec.item_fk)
        for binding in (
            spec.binding_model.objects
            .filter(container=container)
            .select_related(spec.item_fk)
        )
    ]


def get_container_mount_items(container):
    return {
        "projects": get_current_mount_items(container, PROJECT_MOUNT_SPEC),
        "courses": get_current_mount_items(container, COURSE_MOUNT_SPEC),
        "volumes": get_current_mount_items(container, VOLUME_MOUNT_SPEC),
    }
