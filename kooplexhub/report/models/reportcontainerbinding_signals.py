from django.dispatch import receiver
from django.db.models.signals import pre_save, post_save, post_delete, pre_delete
from ..filesystem import publish, remove

@receiver(post_save, sender = ReportContainerBinding)
def launch_report_container(sender, instance, **kwargs):
    try:
        rcb = ReportContainerBinding.objects.get(report=instance)
        start_environment(rcb.container)
        logger.info(f'- Launched pod/container {rcb.container.label} for Report {instance.report..name}')
    except Exception as e:
        logger.warning(f'! check pod/container {rcb.container.label} for Report {instance.report.name}, during launch exception raised: -- {e}')
