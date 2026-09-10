from __future__ import annotations

import posixpath

from django.db import transaction

from ..conf import VOLUME_SETTINGS
from ..models import Volume, UserVolumeBinding
from ..tasks import (
    prepare_attachment_task,
    delete_attachment_task,
)


class VolumeLifecycleError(RuntimeError):
    pass


def attachment_subpath(*, user, folder: str) -> str:
    return VOLUME_SETTINGS.attachment_subpath.format(
        user=user,
        folder=folder,
    )


def create_attachment(*, user, folder, description) -> Volume:
    with transaction.atomic():
        volume = Volume.objects.create(
            folder=folder,
            description=description,
            claim=VOLUME_SETTINGS.attachment_claim,
            subpath=attachment_subpath(
                user=user,
                folder=folder,
            ),
            scope=Volume.Scope.ATTACHMENT,
            provisioning_state=Volume.ProvisioningState.PREPARING,
            allow_shared_write=False,
        )

        UserVolumeBinding.objects.create(
            volume=volume,
            user=user,
            role=UserVolumeBinding.Role.OWNER,
        )

        transaction.on_commit(
            lambda: prepare_attachment_task(volume.pk)
        )

    return volume


def delete_attachment(
    *,
    attachment: Volume,
    actor,
) -> int:
    with transaction.atomic():
        attachment = (
            Volume.objects
            .select_for_update()
            .filter(
                pk=attachment.pk,
                scope=Volume.Scope.ATTACHMENT,
            )
            .first()
        )

        if attachment is None:
            raise VolumeLifecycleError(
                "Attachment does not exist."
            )

        if not (
            actor.is_superuser
            or Volume.objects
            .owned_by(actor)
            .filter(pk=attachment.pk)
            .exists()
        ):
            raise VolumeLifecycleError(
                "You cannot delete this attachment."
            )

        if attachment.containerbindings.exists():
            raise VolumeLifecycleError(
                "Attachment is still bound to one or more environments."
            )

        attachment.provisioning_state = (
            Volume.ProvisioningState.DELETING
        )
        attachment.last_operation_error = ""
        attachment.last_operation_failed_at = None
        attachment.save(
            update_fields=[
                "provisioning_state",
                "last_operation_error",
                "last_operation_failed_at",
            ]
        )

        attachment_id = attachment.pk

        transaction.on_commit(
            lambda: delete_attachment_task(attachment_id)
        )

    return attachment_id




