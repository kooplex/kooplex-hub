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
    create = kwargs.pop('create', False)
    task_kwargs = kwargs.pop('kwargs', {})
    kwargs.update({
        'clocked': ClockedSchedule(clocked_time = when),
        'one_off': True,
        'kwargs': json.dumps(task_kwargs),
    })
    try:
        t_old = PeriodicTask.objects.get(name = kwargs['name'])
        if t_old.clocked:
            t_old.clocked.delete()
        t_old.delete()
        logger.warning(f"Old PeriodicTask {t_old.name} is deleted to avoid conflicts")
    except:
        pass
    try:
        t = PeriodicTask(*args, **kwargs)
    except Exception as e:
        logger.error(f"Error registering task {kwargs} -- {e}")
        raise
    t._saved_save = t.save
    t.save = save
    if create:
        t.save()
    return t


