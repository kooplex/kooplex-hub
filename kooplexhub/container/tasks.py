import logging
import subprocess
import time

import requests, os
from django.utils import timezone
from datetime import datetime

from channels.layers import get_channel_layer
from django_huey import db_task, db_periodic_task, periodic_task, get_queue
from huey import crontab, RetryTask
from asgiref.sync import async_to_sync

from container.models import Container, Image

from .conf import CONTAINER_SETTINGS

from .lib import start_environment, stop_environment


logger = logging.getLogger(__name__)


@periodic_task(crontab(minute="*/5"), queue='container')  # Runs every 5 minutes
def ensure_k8s_watcher_running():
    try:
        # Check if the watcher is running
        output = subprocess.check_output(["pgrep", "-f", "manage.py watch_pods"])
        logger.debug(f"Kubernetes watcher is running: {output.decode().strip()}")
    except subprocess.CalledProcessError:
        # Watcher is not running, so restart it
        logger.warning("Kubernetes watcher is not running. Restarting it...")
        subprocess.Popen(["python", "manage.py", "watch_pods"], 
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


@db_task(queue='container', retries=3, retry_delay=10)
def start_container(user_id, container_id):
    try:
        container=Container.objects.get(user_id=user_id, id=container_id)    
        start_environment(container)
        return "Completed"
    except container.DoesNotExist:
        return "Container not found"


@db_task(queue='container', retries=3, retry_delay=10)
def stop_container(user_id, container_id):
    try:
        container=Container.objects.get(user_id=user_id, id=container_id)    
        stop_environment(container)
        return "Completed"
    except container.DoesNotExist:
        return "Container not found"


@db_periodic_task(crontab(minute="55"), queue='container')  # Runs every hour at 55
def kill_idle():
    url_api = CONTAINER_SETTINGS['proxy']['url']
    url_path = CONTAINER_SETTINGS['proxy']['check_container']
    url = os.path.join(url_api, url_path)
    for c in Container.objects.filter(state__in = [Container.State.RUNNING, Container.State.NEED_RESTART], image__imagetype = Image.TP_PROJECT):
        try:
            resp = requests.get(url = url.format(container = c))
            last_activity = resp.json()['last_activity']
            ts = datetime.strptime(last_activity, '%Y-%m-%dT%H:%M:%S.%fZ')
            elasped_time = timezone.now() - timezone.make_aware(ts)
            # FIXME added +1 because proxy's timezone is different
            if elasped_time.days*24+ elasped_time.seconds / 3600 > c.idletime:          
                c.stop()
        except Exception as e:
            logger.error(f'Failed to check container {c.name} of {c.user.username} -- {e}')

