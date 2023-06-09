import requests
from django.utils import timezone
from datetime import datetime
from celery import shared_task
from celery.utils.log import get_task_logger

from container.models import Container
from kooplexhub.settings import KOOPLEX

logger = get_task_logger(__name__)

@shared_task()
def kill_idle():
    url = KOOPLEX.get('proxy', {}).get('check_container', 'http://proxy:8001/api/routes/notebook/{container.label}')
    logger.debug('Checking container idle time...')
    for c in Container.objects.filter(state = Container.ST_RUNNING):
        try:
            resp = requests.get(url = url.format(container = c))
            last_activity = resp.json()['last_activity']
            ts = datetime.strptime(last_activity, '%Y-%m-%dT%H:%M:%S.%fZ')
            elasped_time = timezone.now() - timezone.make_aware(ts)
            # FIXME added +1 because proxy's timezone is different
            if elasped_time.seconds / 3600 - 1 > c.idletime:
                logger.info(f'Container {c.name} of {c.user.username} is idle for {elasped_time.seconds} seconds, stopping it.')
                c.stop()
        except Exception as e:
            logger.error(f'Failed to check container {c.name} of {c.user.username} -- {e}')
