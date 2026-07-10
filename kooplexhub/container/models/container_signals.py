import logging

from django.db.models.signals import pre_save, post_save, pre_delete, post_delete
from django.dispatch import receiver

from ..lib import stop_environment
from ..models import Container

from kooplexhub.lib.libbase import standardize_str

logger = logging.getLogger(__name__)


CONFIG_RESTART_FIELDS = [
    "requested_node",
    "requested_cpu_m",
    "requested_gpu",
    "requested_memory_mib",
    "requested_uptime_hours",
    "image_id",
    "start_teleport",
    "start_seafile",
]


@receiver(pre_save, sender = Container)
def create_container_label(sender, instance, **kwargs):
    if instance.label:
        return
    try:
        cleanname = standardize_str(instance.name)
        instance.label = f'{instance.user.username}-{cleanname}'
    except Exception as e:
        logger.warning(f'! Label could not be created {instance}: -- {e}')
        raise

@receiver(pre_delete, sender = Container)
def remove_container(sender, instance, **kwargs):
    try:
        stop_environment(instance)
        logger.info(f'- removed pod/container {instance.label}')
    except Exception as e:
        logger.warning(f'! check pod/container {instance.label}, during removal exception raised: -- {e}')


@receiver(pre_save, sender=Container)
def container_needs_restart(sender, instance, **kwargs):
    if not instance.pk:
        return

    update_fields = kwargs.get("update_fields")

    if update_fields is not None:
        update_fields = set(update_fields)

        if not update_fields.intersection(CONFIG_RESTART_FIELDS):
            return

    old = (
        Container.objects
        .filter(pk=instance.pk)
        .only(*CONFIG_RESTART_FIELDS, "state", "restart_reasons")
        .first()
    )

    if old is None:
        return

    changed = [
        field
        for field in CONFIG_RESTART_FIELDS
        if getattr(old, field) != getattr(instance, field)
    ]

    if changed:
        instance.mark_restart(
            "Attributes {} changed".format(", ".join(changed)),
            save=False,
        )

