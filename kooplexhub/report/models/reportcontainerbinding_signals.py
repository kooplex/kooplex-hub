import logging

from django.dispatch import receiver
from django.db.models.signals import pre_save, post_save, post_delete, pre_delete
from ..filesystem import publish, remove
from container.lib import stop_environment, start_environment
from container.models import Container

from .reportcontainerbinding import ReportContainerBinding

logger = logging.getLogger(__name__)

@receiver(post_save, sender = ReportContainerBinding)
def launch_report_container(sender, instance, **kwargs):
    try:
        start_environment(instance.container)
        logger.info(f'- Launched pod/container {instance.container.label} for Report {instance.report.name}')
    except Exception as e:
        logger.warning(f'! check pod/container {instance.container.label} for Report {instance.report.name}, during launch exception raised: -- {e}')

@receiver(pre_delete, sender = ReportContainerBinding)
def stop_report_container(sender, instance, **kwargs):
    try:
        stop_environment(instance.container)
        logger.info(f'- Stop pod/container {instance.container.label} for Report {instance.report.name}')
    except Exception as e:
        logger.warning(f'! check pod/container {instance.container.label} for Report {instance.report.name}, during removal exception raised: -- {e}')

@receiver(post_delete, sender = ReportContainerBinding)
def remove_report_container(sender, instance, **kwargs):
    try:
        container = Container.objects.get(id = instance.container.id)
        container.delete()
        logger.info(f'- Remove pod/container {instance.container.label} for Report {instance.report.name}')
    except Exception as e:
        logger.warning(f'! check pod/container {instance.container.label} for Report {instance.report.name}, during removal exception raised: -- {e}')
