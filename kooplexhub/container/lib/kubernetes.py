import logging
import os
import json
from kubernetes import client, config
from kubernetes.client import *
client.rest.logger.setLevel(logging.WARNING)
from urllib.parse import urlparse
from threading import Timer, Event, Lock

from kooplexhub.lib import now
from .proxy import addroute, removeroute

try:
    from kooplexhub.settings import KOOPLEX
    from kooplexhub.settings import SERVERNAME
    from kooplexhub.settings import REDIS_PASSWORD
except ImportError:
    KOOPLEX = {}

KOOPLEX['kubernetes'].update({})
KOOPLEX['kubernetes']['userdata'].update({})
KOOPLEX['kubernetes']['cache'].update({})

logger = logging.getLogger(__name__)

namespace = KOOPLEX['kubernetes'].get('namespace', 'k8plex-hub')

class ContainerEvents:
    def __init__(self):
        self.l = Lock()
        self.e = {}

    def get(self, k):
        with self.l:
            return self.e[k]

    def get_or_create(self, k):
        with self.l:
            if k in self.e:
                return self.e[k]
            e = Event()
            self.e[k] = e
            return e

    def set(self, k):
        with self.l:
            e = self.e.pop(k)
            e.set()

CE_POOL = ContainerEvents()

def check(container):
    """
@summary: retrieve the container state from kubernetes framework
@returns { 'state': Container:ST, 'message': ... }
    """
    config.load_kube_config()
    v1 = client.CoreV1Api()
    status = { 
        'message': 'No extra information returned',
        'phase': 'Missing',
        'state': container.state,
    }
    try:
        podstatus = v1.read_namespaced_pod_status(namespace = namespace, name = container.label)
        status.update( _parse_podstatus(podstatus) ) #FIXME: deprecate
        waiting = lambda cs: cs.state.waiting and hasattr(cs.state.waiting, 'message') and cs.state.waiting.message
        msg = lambda cs: cs.state.waiting.message
        msg_waiting = '; '.join(map(msg, filter(waiting, podstatus.status.container_statuses))) if podstatus.status.container_statuses else ''
        msg = lambda c: c.message
        msg_cond = '; '.join(map(msg, filter(msg, podstatus.status.conditions))) if podstatus.status.conditions else ''
        status['message'] = f'{msg_waiting}; {msg_cond}' if len(msg_waiting) * len(msg_cond) else f'{msg_waiting}{msg_cond}'
        status['phase'] = podstatus.status.phase

        if container.state == container.ST_STARTING and status.get('state') == container.ST_RUNNING:
            container.state = container.ST_RUNNING
            # FIXME could be cleaner
            #for proxy in container.proxies:
            #    addroute(container, KOOPLEX['proxy']['routes'][proxy.name], proxy.port)
            addroute(container, 'NB_URL', 'NB_PORT')
            addroute(container, 'REPORT_URL', 'REPORT_PORT')
#        else:
#            removeroute(container)

    except client.rest.ApiException as e:
        e_extract = json.loads(e.body)
        message = e_extract['message']
        if message.startswith('pods ') and message.endswith(' not found'):
            container.state = container.ST_NOTPRESENT
        elif container.state in [ container.ST_RUNNING, container.ST_NEED_RESTART ]:
            container.state = container.ST_ERROR
        status['state'] = container.state
        status['message'] += message
    finally:
        logger.debug(f"podstatus: {status}")
        container.state_lastcheck_at = now()
        container.save()
    return status


def storage_resources(volumes):
    mounts = []
    claims = set()
    for volume in volumes:
        mountPath = KOOPLEX['kubernetes']['userdata'].get('mountPath_attachment', '/attachments/{volume.folder}') \
                if volume.scope == volume.SCP_ATTACHMENT else \
                KOOPLEX['kubernetes']['userdata'].get('mountPath_volume', '/volume/{volume.folder}')
        mounts.append({
            "name": volume.claim,
            "mountPath": mountPath.format(volume = volume),
            "subPath": volume.subPath,
            })
        claims.add(volume.claim)
    claimdict = lambda c: { "name": c, "persistentVolumeClaim": { "claimName": c } }
    return { 'mounts': mounts, 'claims': list(map(claimdict, claims)) }


def start(container):
    #event = Event()
    event = CE_POOL.get_or_create(container.id)
    s = check(container)
    if s['state'] != container.ST_NOTPRESENT:
        logger.warning(f'Not starting container {container.label}, which is in a wrong state {container.state}')
        return event 

    config.load_kube_config()
    v1 = client.CoreV1Api()

# from settings.py
#    env_variables = [
#        { "name": "LANG", "value": "en_US.UTF-8" },
#        { "name": "SSH_AUTH_SOCK", "value": f"/tmp/{container.user.username}" }, #FIXME: move to db
#        { "name": "SERVERNAME", "value": SERVERNAME},
#    ]
    env_variables = [ {'name': k, "value": v.format(container = container)} for k,v in KOOPLEX['environmental_variables'].items()]
    #env_variables.extend(container.env_variables)

    pod_ports = []
    svc_ports = []
    for proxy in container.proxies:
        pod_ports.append({
            "containerPort": proxy.port,
            "name": proxy.name, 
        })
        svc_ports.append({
            "port": proxy.port,
            "targetPort": proxy.port,
            "protocol": "TCP",
            "name": proxy.name, 
        })


    # LDAP nslcd.conf
            #V1VolumeMount(name="nslcd", mount_path='/etc/mnt'),
    volume_mounts = [{
        "name": "nslcd",
        "mountPath": KOOPLEX['kubernetes']['nslcd'].get('mountPath_nslcd', '/etc/mnt'),
        "readOnly": True
    },
        V1VolumeMount(name="tokens", mount_path="/.s", read_only=True)
    ]#FIXME: use class objects instead
#            V1Volume(name="nslcd", config_map=V1ConfigMapVolumeSource(name="nslcd", default_mode=420, items=[V1KeyToPath(key="nslcd", path='nslcd.conf')])),
    volumes = [{
        "name": "nslcd",
        "configMap": { "name": "nslcd", "items": [{"key": "nslcd", "path": "nslcd.conf" }]}
    },
        V1Volume(name="tokens", secret=V1SecretVolumeSource(secret_name=f"job-tokens", default_mode=0o444, items=[V1KeyToPath(key=container.user.username, path='job_token')])),#items, change ownership, 0o400: https://stackoverflow.com/questions/49945437/changing-default-file-owner-and-group-owner-of-kubernetes-secrets-files-mounted
    ]  #FIXME: use class objects instead

    volume_mounts.append(V1VolumeMount(name="jobtool", mount_path="/etc/jobtool"))
    volumes.append(V1Volume(name="jobtool", config_map=V1ConfigMapVolumeSource(name="job-py", default_mode=0o777, items=[V1KeyToPath(key="job",path="job")] ))
            )
            
    volume_mounts.append(V1VolumeMount(name="initscripts", mount_path="/.init_scripts"))
    initscripts = [
            V1KeyToPath(key="nsswitch",path="01-nsswitch"),
            V1KeyToPath(key="nslcd",path="02-nslcd"),
            V1KeyToPath(key="usermod",path="03-usermod"),
            V1KeyToPath(key="munge",path="04-munge"),
            V1KeyToPath(key="ssh",path="05-ssh"),
            V1KeyToPath(key="jobtools",path="06-jobtool-path"),
            ]

    if container.user.profile.can_teleport:
        initscripts.append(V1KeyToPath(key="teleport",path="06-teleport"))
        env_variables.append({ "name": "REDIS_PASSWORD", "value": REDIS_PASSWORD })


    if container.start_ssh:
        initscripts.append(V1KeyToPath(key="sshstart",path="07-sshstart"))
        sshport = 2222
        pod_ports.append({
            "containerPort": 22,
            "name": "ssh", 
        })
        svc_ports.append({
            "port": sshport,
            "targetPort": 22,
            "protocol": "TCP",
            "name": "ssh", 
        })


    volumes.append(
            V1Volume(name="initscripts", config_map=V1ConfigMapVolumeSource(name="initscripts", default_mode=0o777, items=initscripts ))
            )
            

    # jobs kubeconf and slurm
    if container.user.profile.can_runjob:
        # SLURM
        #if "munge" in initscripts.data.keys():   
        volume_mounts.append(V1VolumeMount(name="munge", mount_path="/etc/munge_tmp", read_only=True))
        volumes.append(V1Volume(name="munge", config_map=V1ConfigMapVolumeSource(name='munge', default_mode=400, items=[V1KeyToPath(key="munge",path="munge.key")])))
        volume_mounts.append(V1VolumeMount(name="slurmconf", mount_path="/etc/slurm-llnl", read_only=True))
        volumes.append(V1Volume(name="slurmconf", config_map=V1ConfigMapVolumeSource(name='slurmconf', items=[V1KeyToPath(key="slurmconf",path="slurm.conf")])))
    # user's home and garbage
    claim_userdata = False
    if container.image.require_home:
        logger.debug('mount home')
        claim_userdata = True
        volume_mounts.extend([{
            "name": "home",
            "mountPath": KOOPLEX['kubernetes']['userdata'].get('mountPath_home', '/home/{user.username}').format(user = container.user),
            "subPath": KOOPLEX['kubernetes']['userdata'].get('subPath_home', 'home/{user.username}').format(user = container.user),
        }, {
            "name": "garbage",
            "mountPath": KOOPLEX['kubernetes']['userdata'].get('mountPath_garbage', '/home/garbage').format(user = container.user),
            "subPath": KOOPLEX['kubernetes']['userdata'].get('subPath_garbage', 'garbage/{user.username}').format(user = container.user),
        }])
    if claim_userdata:
        volumes.extend([
            {
            "name": "home",
            "persistentVolumeClaim": { "claimName": KOOPLEX['kubernetes']['userdata'].get('claim-home', 'home') }
        },
            {
            "name": "garbage",
            "persistentVolumeClaim": { "claimName": KOOPLEX['kubernetes']['userdata'].get('claim-garbage', 'garbage') }
        }])


    # user's scratch folder
    if container.user.profile.has_scratch:
        volume_mounts.append({
            "name": "scratch",
            "mountPath": KOOPLEX['kubernetes']['userdata'].get('mountPath_scratch', '/v/scratch/{user.username}').format(user = container.user),
            "subPath": KOOPLEX['kubernetes']['userdata'].get('subPath_scratch', '{user.username}').format(user = container.user),
        })
        volumes.append({
            "name": "scratch",
            "persistentVolumeClaim": { "claimName": KOOPLEX['kubernetes']['userdata'].get('claim-scratch', 'scratch') }
        })


    # education
    claim_edu = False
    for course in container.courses:
        logger.debug(f'mount course folders {course.name}')
        claim_edu = True
        volume_mounts.extend([{
            "name": "edu",
            "mountPath": KOOPLEX['kubernetes']['userdata'].get('mountPath_course_workdir', '/course/{course.folder}').format(course = course),
            "subPath": KOOPLEX['kubernetes']['userdata'].get('subPath_course_workdir', 'course_workdir/{course.folder}/{user.username}').format(course = course, user = container.user),
        }, {
            "name": "edu",
            "mountPath": KOOPLEX['kubernetes']['userdata'].get('mountPath_course_public', '/course/{course.folder}.public').format(course = course),
            "subPath": KOOPLEX['kubernetes']['userdata'].get('subPath_course_public', 'course/{course.folder}/public').format(course = course),
        }])
        if course.is_teacher(container.user):
            volume_mounts.extend([{
                "name": "edu",
                "mountPath": KOOPLEX['kubernetes']['userdata'].get('mountPath_course_assignment', '/course/{course.folder}.everyone').format(course = course),
                "subPath": KOOPLEX['kubernetes']['userdata'].get('subPath_course_assignment_all', 'course_assignment/{course.folder}').format(course = course, user = container.user),
            }, {
                "name": "edu",
                "mountPath": KOOPLEX['kubernetes']['userdata'].get('mountPath_course_assignment_prepare', '/course/{course.folder}.prepare').format(course = course),
                "subPath": KOOPLEX['kubernetes']['userdata'].get('subPath_course_assignment_prepare', 'course/{course.folder}/assignment_prepare').format(course = course),
            }, {
                "name": "edu",
                "mountPath": KOOPLEX['kubernetes']['userdata'].get('mountPath_course_assignment_correct', '/course/{course.folder}.correct').format(course = course),
                "subPath": KOOPLEX['kubernetes']['userdata'].get('subPath_course_assignment_correct_all', 'course_assignment/{course.folder}/correctdir').format(course = course, user = container.user),
            }])
        else:
            volume_mounts.extend([{
                "name": "edu",
                "mountPath": KOOPLEX['kubernetes']['userdata'].get('mountPath_course_assignment', '/course/{course.folder}.everyone').format(course = course),
                "subPath": KOOPLEX['kubernetes']['userdata'].get('subPath_course_assignment', 'course_assignment/{course.folder}/{user.username}').format(course = course, user = container.user),
            }])#CORRECTDIR
    if claim_edu:
        volumes.append({
            "name": "edu",
            "persistentVolumeClaim": { "claimName": KOOPLEX['kubernetes']['userdata'].get('claim-edu', 'edu') }
        })


    # project
    claim_project = False
    for project in container.projects:
        volume_mounts.extend([{
             "name": "project",
             "mountPath": KOOPLEX['kubernetes']['userdata'].get('mountPath_project', '/project/{project.subpath}').format(project = project),
             "subPath": KOOPLEX['kubernetes']['userdata'].get('subPath_project', '{project.subpath}').format(project = project, user = container.user),
        }, {
             "name": "project",
             "mountPath": KOOPLEX['kubernetes']['userdata'].get('mountPath_report_prepare', '/report_prepare/{project.subpath}').format(project = project),
             "subPath": KOOPLEX['kubernetes']['userdata'].get('subPath_report_prepare', '{project.subpath}').format(project = project, user = container.user),
        }])
        claim_project = True
    if claim_project:
        volumes.append({
            "name": "project",
            "persistentVolumeClaim": { "claimName": KOOPLEX['kubernetes']['userdata'].get('claim-project', 'project') }
        })

    # report
    claim_report = False
    for report in container.reports:
        volume_mounts.extend([{
             "name": "report",
             "mountPath": '/srv/report', # KOOPLEX['kubernetes']['userdata'].get('mountPath_report', '/srv/report').format(report = report),
             "subPath": KOOPLEX['kubernetes']['userdata'].get('subPath_report', '{report.subpath}').format(report = report),
        }
        ])
        claim_report = True
    if claim_report:
        volumes.append({
            "name": "report",
            "persistentVolumeClaim": { "claimName": KOOPLEX['kubernetes']['userdata'].get('claim-report', 'report') }
        })

    # volumes
    storage = storage_resources(container.volumes)
    volume_mounts.extend(storage['mounts'])
    volumes.extend(storage['claims'])



#    has_report = False
#    has_cache = False
#
#    if container.image.mount_report:
#        if container.image.imagetype == container.image.TP_PROJECT:
#            report_root_folders = []
#            for report in container.reports:
#                if report.project.uniquename in report_root_folders:
#                    continue
#                report_root_folders.append(report.project.uniquename)
#                volume_mounts.append({
#                    "name": "pv-k8plex-hub-report",
#                    "mountPath": os.path.join(mount_point, report_subdir, report.project.name),
#                    #"mountPath": os.path.join(mount_point, report_subdir, f'{report.project.name}-{report.project.groupname}'),
#                    "subPath": report.project.uniquename,
#                    "readOnly": True
#                })
#                has_report = True
#        else:
#            report = container.report
#            volume_mounts.append({
#                "name": "pv-k8plex-hub-report",
#                "mountPath": os.path.join('/srv', 'report', report.cleanname),
#                "subPath": os.path.join(report.project.uniquename, report.cleanname),
#                "readOnly": True
#            })
#            has_report = True
#
#    for sync_lib in container.synced_libraries:
#        o = urlparse(sync_lib.token.syncserver.url)
#        server = o.netloc.replace('.', '_')
#        volume_mounts.append({
#            "name": "pv-k8plex-hub-cache",
#            "mountPath": os.path.join(mount_point, 'synchron', f'{sync_lib.library_name}-{server}'),
#            "subPath": os.path.join('fs', container.user.username, server, 'synchron', sync_lib.library_name),
#        })
#        has_cache = True
#
#    for repo in container.repos:
#        o = urlparse(repo.token.repository.url)
#        server = o.netloc.replace('.', '_')
#        volume_mounts.append({
#            "name": "pv-k8plex-hub-cache",
#            "mountPath": os.path.join(mount_point, 'git', f'{repo.clone_folder}-{server}'),
#            "subPath": os.path.join('git', container.user.username, server, repo.clone_folder),
#        })
#        has_cache = True
#
#    if has_report:
#        volumes.append({
#            "name": "pv-k8plex-hub-report",
#            "persistentVolumeClaim": { "claimName": "pvc-report-k8plex", }
#        })
#    
#    if has_cache:
#        volumes.append({
#            "name": "pv-k8plex-hub-cache",
#            "persistentVolumeClaim": { "claimName": "pvc-cache-k8plex", }
#        })
#

    resources = KOOPLEX['kubernetes'].get('resources', {}).copy()
    pod_resources = {"requests":{}, "limits": {}}
    pod_resources["requests"]["nvidia.com/gpu"] = f"{max(container.gpurequest, resources['requests']['nvidia.com/gpu'])}"
    #pod_resources["requests"]["gpu"] = f"{container.gpurequest}"
    pod_resources["limits"]["nvidia.com/gpu"] = f"{max(container.gpurequest, resources['limits']['nvidia.com/gpu'])}"
    #pod_resources["limits"]["gpu"] = f"{container.gpurequest}"
    pod_resources["requests"]["cpu"] = f"{1000*max(container.cpurequest, resources['requests']['cpu'])}m"
    pod_resources["limits"]["cpu"] = f"{1000*max(container.cpurequest, resources['limits']['cpu'])}m"
    pod_resources["requests"]["memory"] = f"{max(container.memoryrequest, resources['requests']['memory'])}Gi"
    pod_resources["limits"]["memory"] = f"{max(container.memoryrequest, resources['limits']['memory'])}Gi"

#    logger.warning(f"{resources}")

    pod_definition = {
            "apiVersion": "v1",
            "kind": "Pod",
            "metadata": {
                "name": container.label,
                "namespace": namespace,
                "labels": { "lbl": f"lbl-{container.label}",
                    "user": container.user.username}
            },
            "spec": {
                "containers": [{
                    "name": container.label,
                    "command": ["/bin/bash", "-c", f"chmod a+x {container.image.command}; {container.image.command}"],                   
                    "image": container.image.name,
                    "volumeMounts": volume_mounts,
                    "ports": pod_ports,
                    "imagePullPolicy": KOOPLEX['kubernetes'].get('imagePullPolicy', 'IfNotPresent'),
                    "env": env_variables,
                    "resources": pod_resources,
                }],
                "volumes": volumes,
                "nodeSelector": container.target_node, 
            }
        }

    svc_definition = {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {
                "name": container.label,
            },
            "spec": {
                "selector": {
                    "lbl": f"lbl-{container.label}",
                    },
                "ports": svc_ports,
#                "type": "LoadBalancer",
            }
        }

    try:
        v1.create_namespaced_service(namespace = namespace, body = svc_definition)
    except client.rest.ApiException as e:
        logger.warning(e)
        if json.loads(e.body)['code'] != 409: # already exists
            logger.debug(svc_definition)
            raise
    try:
        v1.create_namespaced_pod(namespace = namespace, body = pod_definition)
    except client.rest.ApiException as e:
        logger.warning(e)
        if json.loads(e.body)['code'] != 409: # already exists
            logger.debug(pod_definition)
            raise
    container.state = container.ST_STARTING
    container.save()
    Timer(.2, _check_starting, args = (container.id, event, 300)).start()
    return event


def _check_starting(container_id, event, left = 10):
    from container.models import Container
    try:
        container = Container.objects.get(id = container_id)
        assert container.state == container.ST_STARTING, f'wrong state {container.label} {container.state}'
    except Exception as e:
        logger.warning(e)
        return
    chk = check(container)
    if chk['state'] == Container.ST_RUNNING:
        logger.info(f'+ pod of {container.label} is ready')
        #event.set()
        CE_POOL.set(container_id)
    elif left == 0:
        logger.warning(f"gave up on checking container {container.label}, {chk['message']}")
    else:
        dt = 1.5 * max(1, 10 - left)
        Timer(dt, _check_starting, args = (container.id, event, left - 1)).start()
        logger.debug(f"container {container.label} is still starting (chk['message']). Next check in {dt}")


def stop(container):
    #event = Event()
    event = CE_POOL.get_or_create(container.id)
    s = check(container)
    if s['state'] == container.ST_NOTPRESENT:
        CE_POOL.set(container.id)
        logger.warning(f'Not stopping container {container.label}, which is not present')
        return event 

    container.state = container.ST_STOPPING
    config.load_kube_config()
    v1 = client.CoreV1Api()
    try:
        removeroute(container, 'NB_URL')
        removeroute(container, 'REPORT_URL')
    except Exception as e:
        logger.error(f"Cannot remove proxy route of container {container} -- {e}")
    try:
        msg = v1.delete_namespaced_pod(namespace = namespace, name = container.label)
        logger.debug(msg)
    except client.rest.ApiException as e:
        logger.warning(e)
        if json.loads(e.body)['code'] != 404: # doesnt exists
            raise
        container.state = container.ST_NOTPRESENT
    try:
        msg = v1.delete_namespaced_service(namespace = namespace, name = container.label)
        logger.debug(msg)
    except client.rest.ApiException as e:
        logger.warning(e)
        if json.loads(e.body)['code'] != 404: # doesnt exists
            raise
    container.save()
    if container.state == container.ST_STOPPING:
        Timer(.2, _check_stopping, args = (container.id, event)).start()
    else:
        #event.set()
        CE_POOL.set(container.id)
    return event


def _check_stopping(container_id, event):
    from container.models import Container
    try:
        container = Container.objects.get(id = container_id)
        if container.state == container.ST_NOTPRESENT:
            #event.set()
            CE_POOL.set(container.id)
            return
        assert container.state == container.ST_STOPPING, f'wrong state {container.label} {container.state}'
    except Exception as e:
        logger.warning(e)
        return
    s = check(container)
    if s['state'] == container.ST_NOTPRESENT:
        #event.set()
        CE_POOL.set(container.id)
        logger.info(f'- pod of {container.label} is not present')
    else:
        Timer(1, _check_stopping, args = (container.id, event)).start()
        logger.debug(f'container {container.label} is still present')


def restart(container):
    from container.models import Container
    assert container.state not in [ container.ST_NOTPRESENT, container.ST_STOPPING ], f'container {container.label} is {container.ST_LOOKUP[container.state]}.'
    ev_stop = stop(container)
    if ev_stop.wait(timeout = 30):
        container = Container.objects.get(id = container.id)
        return start(container)
    else:
        logger.error(f'Not restarting container {container.label}. It is taking very long to stop')
        raise Exception(f'Not restarting container {container.label}. It is taking very long to stop.')


def _parse_podstatus(podstatus):
    from container.models import Container
    sts = podstatus.status.container_statuses
    cds = podstatus.status.conditions
    logger.debug(sts)
    logger.debug(cds)

    if podstatus.status.phase == 'Pending':
        return {
       #     'state': Container.state,
       #     'message': 'Pending, image pull?...'
        }

    if cds is not None:
        if cds[0].reason in [ 'Unschedulable', 'BadRequest' ]:
            return {
                'state': Container.ST_ERROR,
                'reason': cds[0].reason,
                'message': cds[0].message
            }
        sts = podstatus.status.container_statuses
        if sts is None:
            return {
                'state': Container.ST_ERROR,
                'reason': 'unknown',
                'message': 'Ask kooplex admins to investigate logs'
            }
        st = sts[0]
        try:
            if st.state.waiting.reason in [ 'CreateContainerConfigError', 'ImagePullBackOff' ]:
                return {
                    'state': Container.ST_ERROR,
                    'reason': st.state.waiting.reason,
                    'message': st.state.waiting.message
                }
        except Exception as e:
            logger.warning(f"Unhandled exception: {e}")
        indicators = []
        if st.started:
            indicators.append('started')
        if st.ready:
            indicators.append('ready')
        indicators.append(f'restarted {st.restart_count} times')
        return {
            'state': Container.ST_RUNNING,
            'message': ', '.join(indicators)
        }


def fetch_containerlog(container):
    v1 = client.CoreV1Api()
    try:
        podlog = v1.read_namespaced_pod_log(namespace = namespace, name = container.label)
        return podlog[-10000:]
    except Exception as e:
        logger.warning(e)
        return "There are no environment log messages yet to retrieve"
