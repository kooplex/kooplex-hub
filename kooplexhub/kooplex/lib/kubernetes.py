import logging
import os
import json
from kubernetes import client, config

from kooplex.settings import KOOPLEX
from .proxy import addroute, removeroute

logger = logging.getLogger(__name__)

def start(environment):
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
        { "name": "NB_USER", "value": environment.user.username },
        { "name": "NB_TOKEN", "value": environment.user.profile.token }
    ]
    for proxy in environment.proxies:
        env_variables.extend(proxy.env_variables)
        pod_ports.append({
            "containerPort": proxy.port,
            "name": "http", 
        })
        svc_ports.append({
            "port": proxy.port,
            "targetPort": proxy.port,
            "protocol": "TCP",
        })
    #FIXME: report env should not have the home
    volumes = [{
        "name": "pv-k8plex-hub-home",
        "persistentVolumeClaim": { "claimName": "pvc-home-k8plex", }
    }]
    volume_mounts = [{
        "name": "pv-k8plex-hub-home",
        "mountPath": os.path.join(mount_point, environment.user.username),
        "subPath": environment.user.username,
    }]
    has_project = False
    for project in environment.projects:
        volume_mounts.append({
            "name": "pv-k8plex-hub-project",
            "mountPath": os.path.join(mount_point, project_subdir, project.uniquename),
            "subPath": project.uniquename
        })
        volume_mounts.append({
            "name": "pv-k8plex-hub-report",
            "mountPath": os.path.join(mount_point, report_subdir, project.uniquename),
            "subPath": project.uniquename,
            "readOnly": True
        })
        volume_mounts.append({
            "name": "pv-k8plex-hub-cache-report",
            "mountPath": os.path.join(mount_point, report_prepare_subdir, project.uniquename),
            "subPath": project.uniquename
        })
        has_project = True
    if has_project:
        volumes.append({
            "name": "pv-k8plex-hub-project",
            "persistentVolumeClaim": { "claimName": "pvc-project-k8plex", }
        })
        volumes.append({
            "name": "pv-k8plex-hub-report",
            "persistentVolumeClaim": { "claimName": "pvc-report-k8plex", }
        })
        volumes.append({
            "name": "pv-k8plex-hub-cache-report",
            "persistentVolumeClaim": { "claimName": "pvc-cache.report-k8plex", }
        })

#FIXME: hardcode
    logger.debug(environment.image)
    image = "basic"
    pod_definition = {
            "apiVersion": "v1",
            "kind": "Pod",
            "metadata": {
                "name": environment.name,
                "namespace": "default",
                "labels": { "lbl": f"lbl-{environment.name}", }
            },
            "spec": {
                "containers": [{
                    "name": environment.name,
                    "image": f"kooplex-test:5000/k8plex-image-{image}",
                    "volumeMounts": volume_mounts,
                    "ports": pod_ports,
                    "imagePullPolicy": "IfNotPresent",
                    "env": env_variables,
                }],
                "volumes": volumes,
            }
        }

    svc_definition = {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {
                "name": environment.name,
            },
            "spec": {
                "selector": {
                    "lbl": f"lbl-{environment.name}",
                    },
                "ports": svc_ports,
            }
        }

    try:
        msg = v1.create_namespaced_service(namespace = "default", body = svc_definition)
        logger.debug(msg)
    except client.rest.ApiException as e:
        logger.warning(e)
        if json.loads(e.body)['code'] != 409: # already exists
            logger.debug(svc_definition)
            raise
    try:
        msg = v1.create_namespaced_pod(namespace = "default", body = pod_definition)
        logger.debug(msg)
    except client.rest.ApiException as e:
        logger.warning(e)
        if json.loads(e.body)['code'] != 409: # already exists
            logger.debug(pod_definition)
            raise
    environment.state = environment.ST_RUNNING
    environment.save()
    addroute(environment)

def stop(environment):
    config.load_kube_config()
    v1 = client.CoreV1Api()
    removeroute(environment)
    try:
        msg = v1.delete_namespaced_pod(namespace = "default", name = environment.name)
        logger.debug(msg)
    except client.rest.ApiException as e:
        logger.warning(e)
        if json.loads(e.body)['code'] != 404: # doesnt exists
            raise
    try:
        msg = v1.delete_namespaced_service(namespace = "default", name = environment.name)
        logger.debug(msg)
    except client.rest.ApiException as e:
        logger.warning(e)
        if json.loads(e.body)['code'] != 404: # doesnt exists
            raise
    environment.state = environment.ST_NOTPRESENT
    environment.save()

def check(environment):
    raise NotImplementedError(environment)
