import logging
import os
import json
from kubernetes import client, config
from kubernetes.client import *

from hub.models.token import Token
from service.models.service import SeafileService
client.rest.logger.setLevel(logging.WARNING)
from urllib.parse import urlparse
from threading import Timer, Event, Lock
from ..models.image import Image

from kooplexhub.lib import now

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

def check(container):
    """
@summary: retrieve the container state from kubernetes framework
@returns { 'state': Container:ST, 'message': ... }
    """
    state_mapper = {
        'Killing': container.ST_STOPPING,
        'Scheduled': container.ST_STARTING,
        'Pulling': container.ST_STARTING,
        'Pulled': container.ST_STARTING,
        'Created': container.ST_STARTING,
        'SandboxChanged': container.ST_STARTING,
        'Started': container.ST_RUNNING,
        'Not present': container.ST_NOTPRESENT,
        'FailedCreatePodSandBox': container.ST_ERROR,
        'FailedMount': container.ST_ERROR,
        'FailedKillPod': container.ST_STOPPING,

        'Running': container.ST_RUNNING,
    }
    #FIXME: if called too frequently, skip to avoid API stress
    logger.info(f"? checking {container.label}")
    previous_state = container.state
    previous_state_backend = container.state_backend
    config.load_kube_config()
    v1 = client.CoreV1Api()
    #FIXME: hardcoded timeout
    events = v1.list_namespaced_event(namespace, field_selector=f'involvedObject.name={container.label}', timeout_seconds = 1).items
    current_state_backend = None
    if len(events):
        current_state_backend=events[-1].reason
        message=events[-1].message
        current_state=state_mapper[current_state_backend]
    if not len(events) or current_state==container.ST_STOPPING:
        try:
            pod_status = v1.read_namespaced_pod_status(namespace = namespace, name = container.label)
            phase=pod_status.status.phase  #FIXME what are the possible values???
            current_state=state_mapper[phase]
            message=pod_status.status.message or "Container found"
            if current_state_backend is None:
                current_state_backend = phase
        except client.rest.ApiException as e:
            if e.reason == 'Not Found':
                current_state_backend=e.reason
                current_state=container.ST_NOTPRESENT
                message="Container not found"
            else:
                raise
    container.state_lastcheck_at = now()
    container.state = current_state
    container.state_backend = current_state_backend
    container.save()
    status = { 
        'message': message,
        'phase': current_state_backend,
        'state': container.state,
        'changed': current_state != previous_state or current_state_backend != previous_state_backend
    }
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

# For Seafile, NextCloud etc WebDAV mounts
def create_sidecar_davfs(container, service):    

    secret_item=[V1KeyToPath(key=service.kubernetes_secret_name, path=service.secret_file)]
    davfs_secret_volume = V1Volume(name="davfs-secrets", secret=V1SecretVolumeSource(
        secret_name=container.user.username,
        default_mode=0o444, 
        items=secret_item))
    secret_volume_mount = V1VolumeMount(name="davfs-secrets", mount_path=service.secret_mount_dir, read_only=True)
                                    
    empty_volume = V1Volume(name="davfs-seafile-empty-dir", empty_dir=V1EmptyDirVolumeSource(medium="", size_limit="30Gi"))
    empty_volume_mount =  V1VolumeMount(name="davfs-seafile-empty-dir", mount_path=service.mount_dir, mount_propagation = "Bidirectional")
    
    container = {
                    "name": "davfs-sidecar",
                    "image": "image-registry.vo.elte.hu/sidecar-davfs2", #FIXME
                    "volumeMounts": [secret_volume_mount, empty_volume_mount],                    
                    "imagePullPolicy": KOOPLEX['kubernetes'].get('imagePullPolicy', 'IfNotPresent'),
                    "env": service.get_envs(container.user),
                    "securityContext": V1SecurityContext(
                        #run_as_user=1029, 
                        privileged= True,
                        capabilities=V1Capabilities(add=["SYS_ADMIN"])
                        )
                }
    # It is different in the usercontainer
    host_empty_volume_mount =  V1VolumeMount(name="davfs-seafile-empty-dir", mount_path=service.mount_dir, mount_propagation = "HostToContainer")
    
#    return container, [secret_volume, empty_volume], [host_empty_volume_mount]
    return container, [davfs_secret_volume, empty_volume], [host_empty_volume_mount]

def start(container):
    logger.info(f"+ starting {container.label}")
    s = check(container)
    if s['state'] != container.ST_NOTPRESENT:
        logger.warning(f'Not starting container {container.label}, which is in a wrong state {container.state}')
        return

    config.load_kube_config()
    v1 = client.CoreV1Api()

# from settings.py
#    env_variables = [
#        { "name": "LANG", "value": "en_US.UTF-8" },
#        { "name": "SSH_AUTH_SOCK", "value": f"/tmp/{container.user.username}" }, #FIXME: move to db
#        { "name": "SERVERNAME", "value": SERVERNAME},
#    ]

    if container.image.imagetype == Image.TP_REPORT:
        env_variables = [ {'name': k, "value": v.format(container = container)} for k,v in KOOPLEX['environmental_variables_report'].items()]
    else:
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
    }
    ]#FIXME: use class objects instead
#            V1Volume(name="nslcd", config_map=V1ConfigMapVolumeSource(name="nslcd", default_mode=420, items=[V1KeyToPath(key="nslcd", path='nslcd.conf')])),
    volumes = [{
        "name": "nslcd",
        "configMap": { "name": "nslcd", "items": [{"key": "nslcd", "path": "nslcd.conf" }]}
    },
    ]  #FIXME: use class objects instead

    volume_mounts.append(V1VolumeMount(name="jobtool", mount_path=KOOPLEX['kubernetes']['jobs'].get("jobpy","jobtool")))
    volumes.append(V1Volume(name="jobtool", config_map=V1ConfigMapVolumeSource(name="job.py", default_mode=0o777, items=[V1KeyToPath(key="job",path="job")] ))
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


#    for repo in container.repos:
#        o = urlparse(repo.token.repository.url)
#        server = o.netloc.replace('.', '_')
#        volume_mounts.append({
#            "name": "pv-k8plex-hub-cache",
#            "mountPath": os.path.join(mount_point, 'git', f'{repo.clone_folder}-{server}'),
#            "subPath": os.path.join('git', container.user.username, server, repo.clone_folder),
#        })
#        has_cache = True

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
    
    container_list = []

    #FIXME check whether user wants cloud access in notebook
    if container.start_seafile:        
        service = SeafileService.objects.first()
        service.sync_pw(container.user)
        c, vs, vms = create_sidecar_davfs(container, service)
        container_list.append(c)
        volumes.extend(vs)
        volume_mounts.extend(vms)

    secret_items = [V1KeyToPath(key=KOOPLEX['kubernetes']['jobs'].get("token_name","job-token"), path=KOOPLEX['kubernetes']['jobs'].get("token_name","job-token"))]
    secret_volume = V1Volume(name="main-secrets", secret=V1SecretVolumeSource(secret_name=container.user.username, 
                                                            default_mode=0o444, 
                                                            items=secret_items
                                                            ))#items, change ownership, 0o400: https://stackoverflow.com/questions/49945437/changing-default-file-owner-and-group-owner-of-kubernetes-secrets-files-mounted
    secret_volumemount = V1VolumeMount(name="main-secrets", mount_path=KOOPLEX['kubernetes']["secrets"].get("mount_dir", "/.secrets"), read_only=True)
    volume_mounts.append(secret_volumemount)

    volumes.append(secret_volume)

    main_container = {
                    "name": container.label,
                    "command": ["/bin/bash", "-c", f"chmod a+x {container.image.command}; {container.image.command}"],                   
                    "image": container.image.name,
                    "volumeMounts": volume_mounts,
                    "ports": pod_ports,
                    "imagePullPolicy": KOOPLEX['kubernetes'].get('imagePullPolicy', 'IfNotPresent'),
                    "env": env_variables,
                    "resources": pod_resources,
                    }
        
    container_list.append(main_container)

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
                "containers": container_list,
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
        logger.warning(f'{container} service exists')
        if json.loads(e.body)['code'] != 409: # already exists
            logger.critical(e)
            raise
    try:
        v1.create_namespaced_pod(namespace = namespace, body = pod_definition)
        container.state = container.ST_STARTING
    except client.rest.ApiException as e:
        logger.warning(f'{container} pod exists')
        if json.loads(e.body)['code'] != 409: # already exists
            logger.critical(e)
            raise
    container.save()


def stop(container):
    logger.info(f"- stopping {container.label}")
    s = check(container)
    if s['state'] == container.ST_NOTPRESENT:
        logger.warning(f'Not stopping container {container.label}, which is not present')
        return
    container.state = container.ST_STOPPING
    container.save()
    config.load_kube_config()
    v1 = client.CoreV1Api()
    try:
        msg = v1.delete_namespaced_pod(namespace = namespace, name = container.label)
    except client.rest.ApiException as e:
        logger.warning(e)
        if json.loads(e.body)['code'] != 404: # doesnt exists
            raise
        container.state = container.ST_NOTPRESENT
    try:
        msg = v1.delete_namespaced_service(namespace = namespace, name = container.label)
    except client.rest.ApiException as e:
        logger.warning(e)
        if json.loads(e.body)['code'] != 404: # doesnt exists
            raise


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
            if st.state.waiting:
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
        podlog = v1.read_namespaced_pod_log(namespace = namespace, name = container.label, container = container.label)
        return podlog[-10000:]
    except Exception as e:
        logger.warning(e)
        return "There are no environment log messages yet to retrieve"
