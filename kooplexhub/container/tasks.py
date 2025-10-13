import logging
import subprocess
import time

import requests, os
from django.utils import timezone
from django.template.loader import render_to_string
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
    except Container.DoesNotExist:
        return "Container not found"


@db_task(queue='container', retries=3, retry_delay=10)
def stop_container(user_id, container_id):
    try:
        container=Container.objects.get(user_id=user_id, id=container_id)    
        stop_environment(container)
        return "Completed"
    except container.DoesNotExist:
        return "Container not found"


def render_progressbar(container, metric, **kw):
    if metric == 'idle':
        html=render_to_string("container/resources/idle.html", {'container': container})
        ref=f"[data-pk={container.pk}][data-name=idletime]"
    elif metric == 'cpu':
        html=render_to_string("container/resources/cpu.html", {'container': container})
        ref=f"[data-pk={container.pk}][data-name=cpu]"
    elif metric == 'mem':
        html=render_to_string("container/resources/memory.html", {'container': container})
        ref=f"[data-pk={container.pk}][data-name=memory]"
    elif metric == 'node':
        html=render_to_string('container/resources/node.html', {'container': container, 'mem_pct': kw.get('memory'), 'cpu_pct': kw.get('cpu')})
        ref=f"[data-pk={container.pk}][data-name=node]"
    else:
        logger.error(f'Unknown metric {metric}')
        return
    channel_layer=get_channel_layer()
    async_to_sync(channel_layer.group_send)(f"container-{container.user.id}", {
          "type": "feedback",
          "container_id": container.id,
          "replace_widgets": { ref: html },
    })


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
            idletime=elasped_time.days*24+ elasped_time.seconds / 3600
            if idletime > c.idletime:
                c.stop()
            else:
                c.idle=idletime
                c.save()
                render_progressbar(c, 'idle')
        except Exception as e:
            logger.error(f'Failed to check container {c.name} of {c.user.username} -- {e}')

def prom_query(query):
    import requests
    BASE = "http://prometheus-k8s.monitoring:9090"  #FIXME put in conf
    r = requests.get(f"{BASE}/api/v1/query", params={"query": query})
    r.raise_for_status()
    return r.json()["data"]["result"]

@periodic_task(crontab(minute="*/1"), queue='container')
def k8s_cpu_usage():
    ns=CONTAINER_SETTINGS['kubernetes']['namespace']
    q_cpu="""
sum by (pod) (
  rate(container_cpu_usage_seconds_total{namespace="%s", container!="", image!=""}[1m])
)
    """%ns
    cpu = prom_query(q_cpu)
    cpu_by_pod = {item["metric"]["pod"]: float(item["value"][1]) for item in cpu}
    for k, v in cpu_by_pod.items():
        c=Container.objects.filter(label=k).first()
        if c and c.is_running:
            c.cpuusage=v
            c.save()
            render_progressbar(c, 'cpu')

@periodic_task(crontab(minute="*/1"), queue='container')
def k8s_mem_usage():
    ns=CONTAINER_SETTINGS['kubernetes']['namespace']
    q_mem="""
sum by (pod) (
  container_memory_working_set_bytes{namespace="%s", container!="", image!=""}
) / 1073741824
"""%ns
    mem = prom_query(q_mem)
    mem_by_pod = {item["metric"]["pod"]: float(item["value"][1]) for item in mem}
    for k, v in mem_by_pod.items():
        c=Container.objects.filter(label=k).first()
        if c and c.is_running:
            c.memoryusage=v
            c.save()
            render_progressbar(c, 'mem')

@periodic_task(crontab(minute="*/1"), queue='container')
def k8s_nodes_usage():
    node_cpu_q="""
100 * (
  sum by (instance) (rate(node_cpu_seconds_total{mode!="idle"}[5m]))
/
  sum by (instance) (rate(node_cpu_seconds_total[5m]))
)
    """

    node_mem_q="""
100 * (1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)
    """
    cpu=prom_query(node_cpu_q)
    mem=prom_query(node_mem_q)
    cpu_by_node = {item["metric"]["instance"]: float(item["value"][1]) for item in cpu}
    mem_by_node = {item["metric"]["instance"]: float(item["value"][1]) for item in mem}
    for node, _cpu in cpu_by_node.items():
        _mem=mem_by_node.get(node)
        logger.debug(f"node: {node} CPU: {_cpu}%, MEM: {_mem}%")
        for container in Container.objects.filter(nodemanifest=node): #FIXME: narrow for running/restart?
            render_progressbar(container, 'node', cpu=_cpu, memory=_mem)

