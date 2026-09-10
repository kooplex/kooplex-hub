from __future__ import annotations

import posixpath

from django.db import transaction

from ..conf import VOLUME_SETTINGS
from ..models import Volume, UserVolumeBinding


class VolumeLifecycleError(RuntimeError):
    pass


def attachment_subpath(*, user, folder: str) -> str:
    return posixpath.join(
        VOLUME_SETTINGS.attachment_subpath,
        str(user.username),
        folder,
    )


def create_attachment(*, user, folder, description) -> Volume:
    with transaction.atomic():
        volume = Volume.objects.create(
            folder=folder,
            description=description,
            claim=VOLUME_SETTINGS.attachment_claim,
            subpath=...,
            scope=Volume.Scope.ATTACHMENT,
            state=Volume.State.PREPARING,
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

        attachment_id = attachment.pk
        attachment.delete()

    return attachment_id




