import logging

from django.db.models.signals import pre_save, post_save, pre_delete, post_delete
from django.dispatch import receiver

from ..lib import stop_environment
from ..models import Container

logger = logging.getLogger(__name__)

@receiver(pre_delete, sender = Container)
def remove_container(sender, instance, **kwargs):
    try:
        stop_environment(instance)
        logger.info(f'- removed pod/container {instance.label}')
    except Exception as e:
        logger.warning(f'! check pod/container {instance.label}, during removal exception raised: -- {e}')



