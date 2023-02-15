from django_celery_beat.models import ClockedSchedule, PeriodicTask
from django.utils import timezone
import json
import logging

logger = logging.getLogger(__name__)

def Task(*args, **kwargs):
    def save():
        t.clocked.save()
        t._saved_save()
        logger.info(f"Registered task: {t.name} to do {t.task}")
    when = kwargs.pop('when', timezone.now())
    task_kwargs = kwargs.pop('kwargs', {})
    kwargs.update({
        'clocked': ClockedSchedule(clocked_time = when),
        'one_off': True,
        'kwargs': json.dumps(task_kwargs),
    })
    try:
        t = PeriodicTask(*args, **kwargs)
    except Exception as e:
        logger.error(f"Error registering task {kwargs} -- {e}")
        raise
    t._saved_save = t.save
    t.save = save
    return t


