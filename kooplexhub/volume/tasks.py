import logging

from django.utils import timezone
from django_huey import db_task

from .models import Volume
from .services.live import broadcast_volume_list_changed
from .services.provisioning import (
    ensure_attachment_storage,
    delete_attachment_storage,
)

logger = logging.getLogger(__name__)


@db_task(
    queue='volume',
)
def prepare_attachment_task(volume_id: int):
    volume = Volume.objects.get(pk=volume_id)

    if volume.scope != Volume.Scope.ATTACHMENT:
        return

    if volume.provisioning_state != Volume.ProvisioningState.PREPARING:
        return

    try:
        ensure_attachment_storage(volume)

        Volume.objects.filter(pk=volume.pk).update(
            provisioning_state=Volume.ProvisioningState.READY,
            last_operation_error="",
            last_operation_failed_at=None,
            provisioned_at=timezone.now(),
        )
        broadcast_volume_list_changed(reason="attachment.ready")

    except Exception as exc:
        Volume.objects.filter(pk=volume.pk).update(
            provisioning_state=Volume.ProvisioningState.FAILED,
            last_operation_error=str(exc),
            last_operation_failed_at=timezone.now(),
        )
        broadcast_volume_list_changed(reason="attachment.failed")
        raise


@db_task(
    queue='volume',
)
def delete_attachment_task(volume_id: int):
    volume = Volume.objects.get(pk=volume_id)

    if volume.scope != Volume.Scope.ATTACHMENT:
        return

    if volume.provisioning_state != Volume.ProvisioningState.DELETING:
        return

    try:
        delete_attachment_storage(volume)
        volume.delete()
        broadcast_volume_list_changed(reason="attachment.deleted")

    except Exception as exc:
        Volume.objects.filter(pk=volume.pk).update(
            provisioning_state=Volume.ProvisioningState.FAILED,
            last_operation_error=str(exc),
            last_operation_failed_at=timezone.now(),
        )
        broadcast_volume_list_changed(reason="attachment.failed")
        raise


