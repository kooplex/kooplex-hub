import logging
import os
import json
from kubernetes import client, config
from urllib.parse import urlparse
from threading import Timer, Event


from kooplex.lib import now
from kooplex.settings import KOOPLEX
from .proxy import addroute, removeroute

logger = logging.getLogger(__name__)

def start(service):
    assert service.state == service.ST_NOTPRESENT, f'service {service.name} is in wrong state {service.state}'
    event = Event()
    spawner_conf = KOOPLEX.get('spawner', {})
    mount_point = spawner_conf.get('volume_mount', '/mnt')
    project_subdir = spawner_conf.get('project_subdir', 'project')
    report_subdir = spawner_conf.get('report_subdir', 'report')
    report_prepare_subdir = spawner_conf.get('report_prepare_subdir', 'report_prepare')

    config.load_kube_config()
    v1 = client.CoreV1Api()

    pod_ports = []
    svc_ports = []
    env_variables = [
        { "name": "LANG", "value": "en_US.UTF-8" },
        { "name": "PREFIX", "value": "k8plex" },
        { "name": "SSH_AUTH_SOCK", "value": f"/tmp/{service.user.username}" },
    ]
    for env in service.env_variables:
        env_variables.append(env)
    for proxy in service.proxies:
        pod_ports.append({
            "containerPort": proxy.port,
            "name": "http", 
        })
        svc_ports.append({
            "port": proxy.port,
            "targetPort": proxy.port,
            "protocol": "TCP",
        })
    volumes = []
    volume_mounts = []
    if service.image.require_home:
        volumes.append({
            "name": "pv-k8plex-hub-home",
            "persistentVolumeClaim": { "claimName": "pvc-home-k8plex", }
        })
        volume_mounts.append({
            "name": "pv-k8plex-hub-home",
            "mountPath": os.path.join(mount_point, service.user.username),
            "subPath": service.user.username,
        })
    has_project = False
    has_report = False
    has_cache = False

    if service.image.mount_project:
        for project in service.projects:
            volume_mounts.append({
                "name": "pv-k8plex-hub-project",
                "mountPath": os.path.join(mount_point, project_subdir, project.uniquename),
                "subPath": project.uniquename
            })
            has_project = True
            volume_mounts.append({
                "name": "pv-k8plex-hub-cache",
                "mountPath": os.path.join(mount_point, report_prepare_subdir, project.uniquename),
                "subPath": os.path.join('report_prepare', project.uniquename)
            })
            has_cache = True

    if service.image.mount_report:
        for report in service.reports:
            volume_mounts.append({
                "name": "pv-k8plex-hub-report",
                "mountPath": os.path.join(mount_point, report_subdir, report.project.uniquename),
                "subPath": report.project.uniquename,
                "readOnly": True
            })
            has_report = True
        try:
            report = service.report
            volume_mounts.append({
                "name": "pv-k8plex-hub-report",
                "mountPath": os.path.join('/srv', 'report', report.cleanname),
                "subPath": os.path.join(report.project.uniquename, report.cleanname),
                "readOnly": True
            })
            has_report = True
        except:
            pass

    for sync_lib in service.synced_libraries:
        o = urlparse(sync_lib.token.syncserver.url)
        server = o.netloc.replace('.', '_')
        volume_mounts.append({
            "name": "pv-k8plex-hub-cache",
            "mountPath": os.path.join(mount_point, 'synchron', f'{sync_lib.library_name}-{server}'),
            "subPath": os.path.join('fs', service.user.username, server, 'synchron', sync_lib.library_name),
        })
        has_cache = True

    for repo in service.repos:
        o = urlparse(repo.token.repository.url)
        server = o.netloc.replace('.', '_')
        volume_mounts.append({
            "name": "pv-k8plex-hub-cache",
            "mountPath": os.path.join(mount_point, 'git', f'{repo.clone_folder}-{server}'),
            "subPath": os.path.join('git', service.user.username, server, repo.clone_folder),
        })
        has_cache = True

    if has_project:
        volumes.append({
            "name": "pv-k8plex-hub-project",
            "persistentVolumeClaim": { "claimName": "pvc-project-k8plex", }
        })

    if has_report:
        volumes.append({
            "name": "pv-k8plex-hub-report",
            "persistentVolumeClaim": { "claimName": "pvc-report-k8plex", }
        })
    
    if has_cache:
        volumes.append({
            "name": "pv-k8plex-hub-cache",
            "persistentVolumeClaim": { "claimName": "pvc-cache-k8plex", }
        })

    pod_definition = {
            "apiVersion": "v1",
            "kind": "Pod",
            "metadata": {
                "name": service.label,
                "namespace": "default",
                "labels": { "lbl": f"lbl-{service.label}", }
            },
            "spec": {
                "containers": [{
                    "name": service.label,
                    "image": service.image.name,
                    "volumeMounts": volume_mounts,
                    "ports": pod_ports,
                    "imagePullPolicy": "IfNotPresent",
                    "env": env_variables,
                }],
                "volumes": volumes,
#                "nodeSelector": { "kubernetes.io/hostname": "veo2" }, # FIXME:
#                "nodeSelector": { "kubernetes.io/hostname": "kooplex-deploy" }, # FIXME:
#                "nodeSelector": { "kubernetes.io/hostname": "work" }, # FIXME:
            }
        }

    svc_definition = {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {
                "name": service.label,
            },
            "spec": {
                "selector": {
                    "lbl": f"lbl-{service.label}",
                    },
                "ports": svc_ports,
            }
        }

    try:
        v1.create_namespaced_service(namespace = "default", body = svc_definition)
    except client.rest.ApiException as e:
        logger.warning(e)
        if json.loads(e.body)['code'] != 409: # already exists
            logger.debug(svc_definition)
            raise
    try:
        v1.create_namespaced_pod(namespace = "default", body = pod_definition)
    except client.rest.ApiException as e:
        logger.warning(e)
        if json.loads(e.body)['code'] != 409: # already exists
            logger.debug(pod_definition)
            raise
    service.state = service.ST_STARTING
    service.save()
    Timer(.2, _check_starting, args = (service.id, event)).start()
    return event

#FIXME: define and implement timeout so that no forever loop is happening
def _check_starting(service_id, event, left = 1000):
    from hub.models import Service
    try:
        service = Service.objects.get(id = service_id)
        assert service.state == service.ST_STARTING, f'wrong state {service.name} {service.state}'
    except Exception as e:
        logger.warning(e)
        return
    chk = check(service)
    if chk is True:
        service.state = service.ST_RUNNING
        service.save()
        logger.info(f'+ pod of {service.name} is ready')
        addroute(service)
        event.set()
    elif chk == -1:
        logger.error(f'? pod of {service.name} oopsed {service.message}')
    else:
        if left == 0:
            logger.error(f'service {service.name} not started')
            service.state = service.ST_ERROR
            service.save()
            return
        Timer(.5, _check_starting, args = (service.id, event, left - 1)).start()
        logger.debug(f'service {service.name} is still starting')

def stop(service):
    event = Event()
    service.state = service.ST_STOPPING
    config.load_kube_config()
    v1 = client.CoreV1Api()
    removeroute(service)
    try:
        msg = v1.delete_namespaced_pod(namespace = "default", name = service.label)
        logger.debug(msg)
    except client.rest.ApiException as e:
        logger.warning(e)
        if json.loads(e.body)['code'] != 404: # doesnt exists
            raise
        service.state = service.ST_NOTPRESENT
    try:
        msg = v1.delete_namespaced_service(namespace = "default", name = service.label)
        logger.debug(msg)
    except client.rest.ApiException as e:
        logger.warning(e)
        if json.loads(e.body)['code'] != 404: # doesnt exists
            raise
    service.save()
    if service.state == service.ST_STOPPING:
        Timer(.2, _check_stopping, args = (service.id, event)).start()
    else:
        event.set()
    return event

def _check_stopping(service_id, event):
    from hub.models import Service
    try:
        service = Service.objects.get(id = service_id)
        if service.state == service.ST_NOTPRESENT:
            event.set()
            return
        assert service.state == service.ST_STOPPING, f'wrong state {service.name} {service.state}'
    except Exception as e:
        logger.warning(e)
        return
    if check(service) == -1:
        service.state = service.ST_NOTPRESENT
        service.save()
        event.set()
        logger.info(f'- pod of {service.name} is not present')
    else:
        Timer(.5, _check_stopping, args = (service.id, event)).start()
        logger.debug(f'service {service.name} is still present')

def restart(service):
    from hub.models import Service
    assert service.state != service.ST_NOTPRESENT, f'service {service.name} is not present.'
    ev_stop = stop(service)
    if ev_stop.wait(timeout = 30):
        service = Service.objects.get(id = service.id)
        return start(service)
    else:
        logger.error(f'Not restarting service {service.name}. It is taking very long to stop')
        raise Exception(f'Not restarting service {service.name}. It is taking very long to stop.')

def check(service):
    config.load_kube_config()
    v1 = client.CoreV1Api()
    try:
        podstatus = v1.read_namespaced_pod_status(namespace='default', name = service.label)
        st = podstatus.status.container_statuses[0]
        try:
            if st.state.waiting.reason == 'CreateContainerConfigError':
                service.state = service.ST_ERROR
                message = st.state.waiting.message
                return -1
        except:
            pass
        indicators = []
        if st.started:
            indicators.append('started')
        if st.ready:
            indicators.append('ready')
        indicators.append(f'restarted {st.restart_count} times')
        message = ', '.join(indicators)
        logger.debug(message)
        return st.ready
    except client.rest.ApiException as e:
        e_extract = json.loads(e.body)
        message = e_extract['message']
        if service.state in [ service.ST_RUNNING, service.ST_NEED_RESTART ]:
            service.state = service.ST_ERROR
        return -1
    finally:
        service.last_message = message
        service.last_message_at = now()
        service.save()
