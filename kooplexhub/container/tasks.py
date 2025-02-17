import logging
import subprocess
import time

import requests, os
from django.utils import timezone
from django.db import connections
from datetime import datetime

from channels.layers import get_channel_layer
from django_huey import db_task, periodic_task, get_queue
from huey import crontab
from asgiref.sync import async_to_sync

from container.models import Container, Image
from kooplexhub.settings import KOOPLEX

from .lib import start_environment, stop_environment
from .lib.proxy import addroute, removeroute


logger = logging.getLogger(__name__)


@periodic_task(crontab(minute="*/5"))  # Runs every 5 minutes
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
    finally:
        connections.close_all()


#FIXME feedback signal received
@db_task(queue = 'container')
def start_container(user_id, container_id):
    channel_layer=get_channel_layer()
    try:
        container=Container.objects.get(user_id=user_id, id=container_id)    
        start_environment(container)
        return "Completed"
    except container.DoesNotExist:
        return "not found"
    finally:
        connections.close_all()


@db_task(queue = 'container')
def stop_container(user_id, container_id):
    channel_layer=get_channel_layer()
    try:
        container=Container.objects.get(user_id=user_id, id=container_id)    
        removeroute(container, 'NB_URL')
        removeroute(container, 'REPORT_URL')
        stop_environment(container)
        return "Completed"
    except container.DoesNotExist:
        return "not found"
    finally:
        connections.close_all()


#@shared_task()
def kill_idle():
    url_api = KOOPLEX.get('proxy', {}).get('url_api', 'http://proxy:8001/api')
    url_path = KOOPLEX.get('proxy', {}).get('check_container_path', 'routes/notebook/{container.label}')
    url = os.path.join(url_api, url_path)
    #logger.debug('Checking container idle time...')
    for c in Container.objects.filter(state__in = [Container.ST_RUNNING, Container.ST_NEED_RESTART], image__imagetype = Image.TP_PROJECT):
        try:
            resp = requests.get(url = url.format(container = c))
            last_activity = resp.json()['last_activity']
            ts = datetime.strptime(last_activity, '%Y-%m-%dT%H:%M:%S.%fZ')
            elasped_time = timezone.now() - timezone.make_aware(ts)
            # FIXME added +1 because proxy's timezone is different
            if elasped_time.days*24+ elasped_time.seconds / 3600 > c.idletime:          
                #logger.info(f'Container {c.name} of {c.user.username} is idle for {elasped_time.seconds} seconds, stopping it.')
                c.stop()
        except Exception as e:
            #logger.error(f'Failed to check container {c.name} of {c.user.username} -- {e}')
            pass
