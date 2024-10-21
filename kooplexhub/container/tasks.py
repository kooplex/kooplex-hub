import time
import requests, os
from django.utils import timezone
from datetime import datetime
#from celery import shared_task
#from celery.utils.log import get_task_logger

from channels.layers import get_channel_layer
from django_huey import task
from asgiref.sync import async_to_sync

from container.models import Container, Image
from kooplexhub.settings import KOOPLEX

from .lib import start_environment, stop_environment
from .lib.proxy import addroute, removeroute

#logger = get_task_logger(__name__)

CHECK_INTERVAL=1 #FIXME: hardcoded timout

@task(queue = 'container')
def start_container(user_id, container_id):
    channel_layer=get_channel_layer()
    container=Container.objects.get(user_id=user_id, id=container_id)    
    start_environment(container)
    while True:
        time.sleep(CHECK_INTERVAL)
        status = container.check_state()
        if status['changed']:
            async_to_sync(channel_layer.group_send)("container", {
                    "type": "feedback",
                    "feedback": status['message'],
                    "container_id": container.id,
                    "container_state": container.state,
                    "container_state_backend": container.state_backend,
                })
        if container.state == container.ST_RUNNING:
            addroute(container, 'NB_URL', 'NB_PORT')
            addroute(container, 'REPORT_URL', 'REPORT_PORT')
            break
        elif container.state == container.ST_ERROR:
            break
    return "Completed"


@task(queue = 'container')
def stop_container(user_id, container_id):
    channel_layer=get_channel_layer()
    container=Container.objects.get(user_id=user_id, id=container_id)    
    removeroute(container, 'NB_URL')
    removeroute(container, 'REPORT_URL')
    stop_environment(container)
    while True:
        time.sleep(CHECK_INTERVAL)
        status = container.check_state()
        if status['changed']:
            async_to_sync(channel_layer.group_send)("container", {
                    "type": "feedback",
                    "feedback": status['message'],
                    "container_id": container.id,
                    "container_state": container.state,
                    "container_state_backend": container.state_backend,
                })
        if container.state==container.ST_NOTPRESENT:
            break
    return "Completed"


#FIXME !!!
@task(queue = 'container')
def restart_container(user_id, container_id):
    channel_layer=get_channel_layer()
    container=Container.objects.get(user_id=user_id, id=container_id)    
    stop_environment(container)
    while True:
        time.sleep(CHECK_INTERVAL)
        status = container.check_state()
        if status['changed']:
            async_to_sync(channel_layer.group_send)("container", {
                    "type": "feedback",
                    "feedback": status['message'],
                    "container_id": container.id,
                    "container_state": container.state,
                    "container_state_backend": container.state_backend,
                })
        if container.state == container.ST_NOTPRESENT:
            break
    start_environment(container)
    while True:
        time.sleep(CHECK_INTERVAL)
        status = container.check_state()
        if status['changed']:
            async_to_sync(channel_layer.group_send)("container", {
                    "type": "feedback",
                    "feedback": status['message'],
                    "container_id": container.id,
                    "container_state": container.state,
                    "container_state_backend": container.state_backend,
                })
        if container.state == container.ST_RUNNING:
            addroute(container, 'NB_URL', 'NB_PORT')
            addroute(container, 'REPORT_URL', 'REPORT_PORT')
            break
        elif container.state == container.ST_ERROR:
            break
    return "Completed"



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
