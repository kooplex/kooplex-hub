import logging

from django.db.models.signals import pre_save, post_save, pre_delete, post_delete
from django.dispatch import receiver

from ..lib import stop_environment
from ..models import Container

from kooplexhub.lib.libbase import standardize_str

logger = logging.getLogger(__name__)

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


@receiver(pre_save, sender = Container)
def container_needs_restart(sender, instance, **kwargs):
    if not instance.id:
        return
    old = Container.objects.get(id = instance.id)
    chg = []
    for a in [ 'node', 'cpurequest', 'gpurequest', 'memoryrequest', 'idletime', 'image', 'start_teleport', 'start_seafile' ]:
        if getattr(old, a) != getattr(instance, a):
            chg.append(a)
    if chg:
        instance.mark_restart("Attributes {} changed".format(", ".join(chg)), save = False)
