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

#################################################
#
from django.db.models.signals import pre_save
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.template.loader import render_to_string

@receiver(pre_save, sender=Container)
def on_volume_pre_save(sender, instance, **kwargs):
    if not instance.pk:
        return
    changed = instance.tracker.changed()
    replace_widgets = {}
    messages = [f"chg {changed}"]
    if 'restart_reasons' in changed:
        replace_widgets[f"[data-action=restart][data-pk={instance.pk}]"] = render_to_string("container/button/restart.html", {'container': instance})
    if 'name' in changed:
        from ..templatetags.container_tags import render_name
        old = instance.tracker.previous('name')
        new = instance.name
        messages.append(f"container name changed from {old} to {new}")
        replace_widgets[f"[data-name=name][data-pk={instance.pk}][data-model=container]"] = render_name(instance)
    channel_layer=get_channel_layer()
    async_to_sync(channel_layer.group_send)(f"container-{instance.user.pk}", {
          "type": "feedback",
          "feedback": ", ".join(messages),
          "replace_widgets": replace_widgets,
    })
