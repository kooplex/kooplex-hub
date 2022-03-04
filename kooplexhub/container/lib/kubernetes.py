import logging
import os
import json
from kubernetes import client, config
from urllib.parse import urlparse
from threading import Timer, Event

from kooplexhub.lib import now
from hub.lib.dirname import mp_scratch #FIXME
from .proxy import addroute, removeroute

try:
    from kooplexhub.settings import KOOPLEX
except ImportError:
    KOOPLEX = {}

KOOPLEX['kubernetes'].update({})
KOOPLEX['kubernetes']['userdata'].update({})
KOOPLEX['kubernetes']['cache'].update({})

logger = logging.getLogger(__name__)

namespace = KOOPLEX['kubernetes'].get('namespace', 'k8plex-hub')

def start(container):
    assert container.state == container.ST_NOTPRESENT, f'container {container.label} is in wrong state {container.state}'
    event = Event()

    config.load_kube_config()
    v1 = client.CoreV1Api()

    pod_ports = []
    svc_ports = []
    env_variables = [
        { "name": "LANG", "value": "en_US.UTF-8" },
        { "name": "PREFIX", "value": "k8plex" },
        { "name": "SSH_AUTH_SOCK", "value": f"/tmp/{container.user.username}" },
    ]
    for env in container.env_variables:
        env_variables.append(env)
    for proxy in container.proxies:
        pod_ports.append({
            "containerPort": proxy.port,
            "name": "http", 
        })
        svc_ports.append({
            "port": proxy.port,
            "targetPort": proxy.port,
            "protocol": "TCP",
        })

    # LDAP nslcd.conf
    volume_mounts = [{
        "name": "nslcd",
        "mountPath": KOOPLEX['kubernetes']['nslcd'].get('mountPath_nslcd', '/etc/mnt'),
        "readOnly": True}]
    
    volumes = [{
        "name": "nslcd",
        "configMap": { "name": "nslcd", "items": [{"key": "nslcd", "path": "nslcd.conf" }]}
    }]

    # jobs kubeconf
    if container.user.profile.can_runjob:
        volume_mounts.append({
            "name": "kubeconf",
            "mountPath": '/.secrets/kubeconfig/',
            "readOnly": True})
        env_variables.append({ "name": "KUBECONFIG", "value": "/.secrets/kubeconfig/config" })
        volumes.append({
            "name": "kubeconf",
            "configMap": { "name": KOOPLEX['kubernetes'].get('kubeconfig_job', 'kubeconfig'), "items": [{"key": "kubejobsconfig", "path": "config" }]}
        })


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


    for course in container.courses:
        logger.debug(f'mount course folders {course.name}')
        claim_userdata = True
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

    claim_attachment = False

    for attachment in container.attachments:
        volume_mounts.extend([{
             "name": "attachment",
             "mountPath": KOOPLEX['kubernetes']['userdata'].get('mountPath_attachment', '/attachment/{attachment.folder}').format(attachment = attachment),
             "subPath": KOOPLEX['kubernetes']['userdata'].get('subPath_attachment', '{attachment.folder}').format(attachment = attachment, user = container.user),
        }
        ])
        claim_attachment = True

    claims = set()
    for volume in container.volumes:
        volume_mounts.append({
            "name": volume.claim,
            "mountPath": KOOPLEX['kubernetes']['userdata'].get('mountPath_volume', '/volume/{volume.cleanname}').format(volume = volume),
            "subPath": volume.subPath
        })
        claims.add(volume.claim)
    claimdict = lambda c: { "name": c, "persistentVolumeClaim": { "claimName": c } }
    volumes.extend(map(claimdict, claims))

    if claim_userdata:
        volumes.extend([
            {
            "name": "home",
            "persistentVolumeClaim": { "claimName": KOOPLEX['kubernetes']['userdata'].get('claim-home', 'home') }
        },
            {
            "name": "garbage",
            "persistentVolumeClaim": { "claimName": KOOPLEX['kubernetes']['userdata'].get('claim-garbage', 'garbage') }
        },
            {
            "name": "edu",
            "persistentVolumeClaim": { "claimName": KOOPLEX['kubernetes']['userdata'].get('claim-edu', 'edu') }
        },
            ])

    if claim_project:
        volumes.append(
            {
            "name": "project",
            "persistentVolumeClaim": { "claimName": KOOPLEX['kubernetes']['userdata'].get('claim-project', 'project') }
        }
            )

    if claim_attachment:
        volumes.append(
            {
            "name": "attachment",
            "persistentVolumeClaim": { "claimName": KOOPLEX['kubernetes']['userdata'].get('claim-attachment', 'attachment') }
        }
            )


#    has_report = False
#    has_cache = False
#    has_attachment = False
#
#    if container.image.mount_project:
#        groups = []
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
#    if has_project:
#        volumes.append({
#            "name": "pv-k8plex-hub-project",
#            "persistentVolumeClaim": { "claimName": "pvc-project-k8plex", }
#        })
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

    pod_definition = {
            "apiVersion": "v1",
            "kind": "Pod",
            "metadata": {
                "name": container.label,
                "namespace": namespace,
                "labels": { "lbl": f"lbl-{container.label}", }
            },
            "spec": {
                "containers": [{
                    "name": container.label,
                    "image": container.image.name,
                    "volumeMounts": volume_mounts,
                    "ports": pod_ports,
                    "imagePullPolicy": KOOPLEX['kubernetes'].get('imagePullPolicy', 'IfNotPresent'),
                    "env": env_variables,
                    "resources": KOOPLEX['kubernetes'].get('resources', '{}'),
                }],
                "volumes": volumes,
                "nodeSelector": KOOPLEX['kubernetes'].get('nodeSelector_k8s'), 
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
    Timer(.2, _check_starting, args = (container.id, event)).start()
    return event


def _check_starting(container_id, event, left = 1000):
    from container.models import Container
    try:
        container = Container.objects.get(id = container_id)
        assert container.state == container.ST_STARTING, f'wrong state {container.label} {container.state}'
    except Exception as e:
        logger.warning(e)
        return
    chk = check(container)
    if chk is True:
        logger.info(f'+ pod of {container.label} is ready')
        event.set()
    elif chk == -1:
        logger.error(f'? pod of {container.label} oopsed {container.last_message}')
    else:
        if left == 0:
            logger.error(f'container {container.label} not started')
            container.state = container.ST_ERROR
            container.save()
            return
        Timer(.5, _check_starting, args = (container.id, event, left - 1)).start()
        logger.debug(f'container {container.label} is still starting')


def stop(container):
    logger.debug(f"KKKK {container}")
    event = Event()
    #FIXME
    #event.set()
    #return event
    container.state = container.ST_STOPPING
    config.load_kube_config()
    v1 = client.CoreV1Api()
    try:
        removeroute(container)
    except Exception as e:
        logger.error(f"Cannot remove proxy route of container {container} -- {e}")
    logger.debug(f"KKKK {container}")
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
        event.set()
    return event


def _check_stopping(container_id, event):
    from container.models import Container
    try:
        container = Container.objects.get(id = container_id)
        if container.state == container.ST_NOTPRESENT:
            event.set()
            return
        assert container.state == container.ST_STOPPING, f'wrong state {container.label} {container.state}'
    except Exception as e:
        logger.warning(e)
        return
    if check(container) == -1:
        container.state = container.ST_NOTPRESENT
        container.save()
        event.set()
        logger.info(f'- pod of {container.label} is not present')
    else:
        Timer(.5, _check_stopping, args = (container.id, event)).start()
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


def check(container):
    config.load_kube_config()
    v1 = client.CoreV1Api()
    message = 'no status message to read yet'
    try:
        podstatus = v1.read_namespaced_pod_status(namespace = namespace, name = container.label)
        cds = podstatus.status.conditions
        if cds is not None:
            logger.debug(cds)
        #    container.state = container.ST_ERROR
        #    return -1
            if cds[0].reason == 'Unschedulable':
                container.state = container.ST_ERROR
                message = cds[0].message
                return -1
        sts = podstatus.status.container_statuses
        if sts is None:
            return -1
        st = sts[0]
        try:
            if st.state.waiting.reason == 'CreateContainerConfigError':
                container.state = container.ST_ERROR
                message = st.state.waiting.message
                return -1
            if st.state.waiting.reason == 'ImagePullBackOff':
                container.state = container.ST_ERROR
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

        if container.state == container.ST_STARTING and st.ready:
            container.state = container.ST_RUNNING
            addroute(container)

        return st.ready
    except client.rest.ApiException as e:
        e_extract = json.loads(e.body)
        message = e_extract['message']
        if container.state in [ container.ST_RUNNING, container.ST_NEED_RESTART ]:
            container.state = container.ST_ERROR
        return -1
    finally:
        container.last_message = message
        if message.startswith('pods ') and message.endswith(' not found'):
            container.state = container.ST_NOTPRESENT
        container.last_message_at = now()
        container.save()
