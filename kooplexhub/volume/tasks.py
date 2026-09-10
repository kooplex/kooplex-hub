import logging

from django.utils import timezone
from django_huey import db_task

from .models import Volume
from .services.provisioning import (
    ensure_attachment_storage,
    delete_attachment_storage,
)

logger = logging.getLogger(__name__)


@db_task()
def prepare_attachment_task(volume_id: int):
    volume = Volume.objects.get(pk=volume_id)

    if volume.scope != Volume.Scope.ATTACHMENT:
        return

    if volume.provisioning_state == Volume.ProvisioningState.READY:
        return

    try:
        ensure_attachment_storage(volume)

        Volume.objects.filter(pk=volume.pk).update(
            provisioning_state=Volume.ProvisioningState.READY,
            last_operation_error="",
            last_operation_failed_at=None,
            provisioned_at=timezone.now(),
        )

    except Exception as exc:
        Volume.objects.filter(pk=volume.pk).update(
            provisioning_state=Volume.ProvisioningState.FAILED,
            last_operation_error=str(exc),
            last_operation_failed_at=timezone.now(),
        )
        raise


@db_task()
def delete_attachment_task(volume_id: int):
    volume = Volume.objects.get(pk=volume_id)

    try:
        delete_attachment_storage(volume)
        volume.delete()

    except Exception as exc:
        Volume.objects.filter(pk=volume.pk).update(
            provisioning_state=Volume.ProvisioningState.FAILED,
            last_operation_error=str(exc),
            last_operation_failed_at=timezone.now(),
        )
        raise


