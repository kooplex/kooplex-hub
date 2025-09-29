import logging
import uuid
import os
import json
from kubernetes import client, config
from kubernetes.client import *

from hub.models.token import Token
from service.models.service import SeafileService
client.rest.logger.setLevel(logging.WARNING)
from urllib.parse import urlparse
from threading import Timer, Event, Lock
from ..models import Image, Container

from kooplexhub.lib import now

from kooplexhub.settings import SERVERNAME
from kooplexhub.settings import REDIS_PASSWORD

from ..conf import CONTAINER_SETTINGS
from hub.conf import HUB_SETTINGS
from education.conf import EDUCATION_SETTINGS
from project.conf import PROJECT_SETTINGS
from report.conf import REPORT_SETTINGS
from volume.conf import VOLUME_SETTINGS


#FIXME get rid of it
from kooplexhub.settings import KOOPLEX

logger = logging.getLogger(__name__)

namespace = CONTAINER_SETTINGS['kubernetes']['namespace']



def fetch_containerlog(container):
    v1 = client.CoreV1Api()
    try:
        podlog = v1.read_namespaced_pod_log(namespace = namespace, name = container.label, container = container.label)
        return podlog[-10000:]
    except Exception as e:
        logger.warning(e)
        return "There are no environment log messages yet to retrieve"


def storage_resources(volumes):
    mounts = []
    claims = set()
    for volume in volumes:
        mountPath = VOLUME_SETTINGS['mounts']['attachment']['mountpoint'] \
                if volume.scope == volume.Scope.ATTACHMENT else \
                VOLUME_SETTINGS['mounts']['volume']['mountpoint']
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
                    "imagePullPolicy": CONTAINER_CSETTINGS['kubernetes']['imagePullPolicy'],
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

class MyClaimsAndVolumes:
    def __init__(self):
        self._c=[]
        self._v=[]
        self._l={}
    def add(self, mountPath, subPath, claimName):
        if claimName in self._l:
            c=self._l[claimName]
        else:
            c=str(uuid.uuid4())
            self._l[claimName]=c
            self._c.append({
                    "name": c,
                    "persistentVolumeClaim": { "claimName": claimName }
               })
        self._v.append({
            "name": c,
            "mountPath": mountPath,
            "subPath": subPath,
        })

    def add_cm(self, mountPath, configMap, claimName):
        if claimName in self._l:
            c=self._l[claimName]
        else:
            c=str(uuid.uuid4())
            self._l[claimName]=c
            self._c.append(
                    V1Volume(name=c, config_map=configMap,
                             )
               )
        self._v.append(
            V1VolumeMount(
                name=c, 
                mount_path=mountPath ,
            )
        )


    @property
    def claims(self):
        return self._c

    @property
    def volumes(self):
        return self._v

def start(container):
    logger.info(f"+ starting {container.label}")
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

    env_variables.extend(container.env_variables)
    logger.info(f" ENV {env_variables}")

    pod_ports = []
    svc_ports = []
    logger.info(f" PROXY {container.proxies}")
    for proxy in container.proxies:
        logger.info(f" {proxy}, {proxy.svc_port}")
        pod_ports.append({
            "containerPort": proxy.svc_port,
            "name": proxy.name, 
        })
        svc_ports.append({
            "port": proxy.svc_port,
            "targetPort": proxy.svc_port,
            "protocol": "TCP",
            "name": proxy.name, 
        })


    mCV=MyClaimsAndVolumes()
    logger.debug('mount nslcd')
    mCV.add_cm(
            claimName='nslcd',
            mountPath=CONTAINER_SETTINGS['kubernetes']['nslcd']['mountPath_nslcd'],
            configMap=V1ConfigMapVolumeSource(name="nslcd", default_mode=0o400, items=[V1KeyToPath(key="nslcd",path="nslcd.conf")])
            )

    logger.debug('mount jobpy')
    mCV.add_cm(
        claimName='jobtool',
        mountPath=CONTAINER_SETTINGS['kubernetes']['jobs']["jobpy"],
        configMap=V1ConfigMapVolumeSource(name="job.py", default_mode=0o777, items=[V1KeyToPath(key="job",path="job")] ),
        )
            
            
    logger.debug('mount initscripts')
    initscripts = [
            V1KeyToPath(key="nsswitch",path="01-nsswitch"),
            V1KeyToPath(key="nslcd",path="02-nslcd"),
            V1KeyToPath(key="usermod",path="03-usermod"),
    #        V1KeyToPath(key="ssh",path="05-ssh"),
            ]

    if container.user.profile.can_teleport and container.start_teleport:
        initscripts.append(V1KeyToPath(key="teleport",path="06-teleport"))
        env_variables.append({ "name": "REDIS_PASSWORD", "value": REDIS_PASSWORD })

    mCV.add_cm(
        claimName='initscripts',
        mountPath=CONTAINER_SETTINGS['kubernetes']['initscripts']["mountPath_initscripts"],
        configMap=V1ConfigMapVolumeSource(name="initscripts", default_mode=0o777, items=initscripts),
        )


#    if container.start_ssh:
#        initscripts.append(V1KeyToPath(key="sshstart",path="07-sshstart"))
#        sshport = 2222
#        pod_ports.append({
#            "containerPort": 22,
#            "name": "ssh", 
#        })
#        svc_ports.append({
#            "port": sshport,
#            "targetPort": 22,
#            "protocol": "TCP",
#            "name": "ssh", 
#        })



    # jobs kubeconf and slurm
    #if container.user.profile.can_runjob:
    #    # SLURM
    #    #if "munge" in initscripts.data.keys():   
    #    volume_mounts.append(V1VolumeMount(name="munge", mount_path="/etc/munge_tmp", read_only=True))
    #    volumes.append(V1Volume(name="munge", config_map=V1ConfigMapVolumeSource(name='munge', default_mode=400, items=[V1KeyToPath(key="munge",path="munge.key")])))
    #    volume_mounts.append(V1VolumeMount(name="slurmconf", mount_path="/etc/slurm-llnl", read_only=True))
    #    volumes.append(V1Volume(name="slurmconf", config_map=V1ConfigMapVolumeSource(name='slurmconf', items=[V1KeyToPath(key="slurmconf",path="slurm.conf")])))
    # user's home and garbage
    if container.image.require_home:
        logger.debug('mount home')
        mCV.add(
                mountPath=HUB_SETTINGS['mounts']['home']['mountpoint'].format(user = container.user),
                subPath=HUB_SETTINGS['mounts']['home']['subpath'].format(user = container.user),
                claimName=HUB_SETTINGS['mounts']['home']['claim']
                )
        mCV.add(
                mountPath=HUB_SETTINGS['mounts']['garbage']['mountpoint'].format(user = container.user),
                subPath=HUB_SETTINGS['mounts']['garbage']['subpath'].format(user = container.user),
                claimName=HUB_SETTINGS['mounts']['garbage']['claim']
                )


    # user's scratch folder
    if container.user.profile.has_scratch:
        mCV.add(
                mountPath=HUB_SETTINGS['mounts']['scratch']['mountpoint'].format(user = container.user),
                subPath=HUB_SETTINGS['mounts']['scratch']['subpath'].format(user = container.user),
                claimName=HUB_SETTINGS['mounts']['scratch']['claim']
                )

    # education
    for course in container.courses:
        logger.debug(f'mount course folders {course.name}')
        mCV.add(
                mountPath=EDUCATION_SETTINGS['mounts']['workdir']['mountpoint'].format(user = container.user, course = course),
                subPath=EDUCATION_SETTINGS['mounts']['workdir']['subpath'].format(user = container.user, course = course),
                claimName=EDUCATION_SETTINGS['mounts']['workdir']['claim']
                )
        mCV.add(
                mountPath=EDUCATION_SETTINGS['mounts']['public']['mountpoint'].format(user = container.user, course = course),
                subPath=EDUCATION_SETTINGS['mounts']['public']['subpath'].format(course = course),
                claimName=EDUCATION_SETTINGS['mounts']['public']['claim']
                )
        if course.is_teacher(container.user):
            mCV.add(
                mountPath=EDUCATION_SETTINGS['mounts']['assignment']['mountpoint'].format(user = container.user, course = course),
                subPath=EDUCATION_SETTINGS['mounts']['assignment']['subpath_teacher'].format(course = course),
                claimName=EDUCATION_SETTINGS['mounts']['assignment']['claim']
                    )
            mCV.add(
                mountPath=EDUCATION_SETTINGS['mounts']['assignment_prepare']['mountpoint'].format(user = container.user, course = course),
                subPath=EDUCATION_SETTINGS['mounts']['assignment_prepare']['subpath'].format(course = course),
                claimName=EDUCATION_SETTINGS['mounts']['assignment_prepare']['claim']
                    )
            mCV.add(
                mountPath=EDUCATION_SETTINGS['mounts']['assignment_correct']['mountpoint'].format(user = container.user, course = course),
                subPath=EDUCATION_SETTINGS['mounts']['assignment_correct']['subpath_teacher'].format(course = course),
                claimName=EDUCATION_SETTINGS['mounts']['assignment_correct']['claim']
                    )
        else:
            mCV.add(
                mountPath=EDUCATION_SETTINGS['mounts']['assignment']['mountpoint'].format(user = container.user, course = course),
                subPath=EDUCATION_SETTINGS['mounts']['assignment']['subpath_student'].format(user = container.user, course = course),
                claimName=EDUCATION_SETTINGS['mounts']['assignment']['claim']
                    )
            mCV.add(
                mountPath=EDUCATION_SETTINGS['mounts']['assignment_correct']['mountpoint'].format(user = container.user, course = course),
                subPath=EDUCATION_SETTINGS['mounts']['assignment_correct']['subpath_student'].format(user = container.user, course = course),
                claimName=EDUCATION_SETTINGS['mounts']['assignment_correct']['claim']
                    )

    # project
    for project in container.projects:
        logger.debug(f'mount project folders {project.name}')
        mCV.add(
                mountPath=PROJECT_SETTINGS['mounts']['project']['mountpoint'].format(user = container.user, project = project),
                subPath=PROJECT_SETTINGS['mounts']['project']['subpath'].format(user = container.user, project = project),
                claimName=PROJECT_SETTINGS['mounts']['project']['claim']
                )
        mCV.add(
                mountPath=REPORT_SETTINGS['mounts']['prepare']['mountpoint'].format(user = container.user, project = project),
                subPath=REPORT_SETTINGS['mounts']['prepare']['subpath'].format(user = container.user, project = project),
                claimName=REPORT_SETTINGS['mounts']['prepare']['claim']
                )
      
    # report
#    claim_report = False
#    for report in container.reports:
#        volume_mounts.extend([{
#             "name": "report",
#             "mountPath": '/srv/report', # KOOPLEX['kubernetes']['userdata'].get('mountPath_report', '/srv/report').format(report = report),
#             "subPath": KOOPLEX['kubernetes']['userdata'].get('subPath_report', '{report.subpath}').format(report = report),
#        }
#        ])
#        claim_report = True
#    if claim_report:
#        volumes.append({
#            "name": "report",
#            "persistentVolumeClaim": { "claimName": KOOPLEX['kubernetes']['userdata'].get('claim-report', 'report') }
#        })

    # volumes
    storage = storage_resources(container.volumes)
    volume_mounts=mCV.volumes
    volumes=mCV.claims
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

    #FIXME: now reqeusts=limits are hardcoded
    r=CONTAINER_SETTINGS['kubernetes']['resources']
    pod_resources = {"requests":{}, "limits": {}}
    pod_resources["requests"]["nvidia.com/gpu"] = f"{max(container.gpurequest, r['limit_gpu'])}"
    pod_resources["limits"]["nvidia.com/gpu"] = f"{max(container.gpurequest, r['limit_gpu'])}"
    pod_resources["requests"]["cpu"] = f"{1000*max(container.cpurequest, r['limit_cpu'])}m"
    pod_resources["limits"]["cpu"] = f"{1000*max(container.cpurequest, r['limit_cpu'])}m"
    pod_resources["requests"]["memory"] = f"{max(container.memoryrequest, r['limit_memory'])}Gi"
    pod_resources["limits"]["memory"] = f"{max(container.memoryrequest, r['limit_memory'])}Gi"

    
    container_list = []

    #FIXME check whether user wants cloud access in notebook
    if container.start_seafile:        
        service = SeafileService.objects.first()
        service.sync_pw(container.user)
        c, vs, vms = create_sidecar_davfs(container, service)
        container_list.append(c)
        volumes.extend(vs)
        volume_mounts.extend(vms)

    secret_items = [V1KeyToPath(key=CONTAINER_SETTINGS['kubernetes']['jobs']["token_name"], path=CONTAINER_SETTINGS['kubernetes']['jobs']["token_name"])]
    secret_volume = V1Volume(name="main-secrets", secret=V1SecretVolumeSource(secret_name=container.user.username, 
                                                            default_mode=0o444, 
                                                            items=secret_items
                                                            ))#items, change ownership, 0o400: https://stackoverflow.com/questions/49945437/changing-default-file-owner-and-group-owner-of-kubernetes-secrets-files-mounted
    secret_volumemount = V1VolumeMount(name=CONTAINER_SETTINGS['kubernetes']["secrets"]["name"], mount_path=CONTAINER_SETTINGS['kubernetes']["secrets"]["mount_dir"], read_only=True)
    volume_mounts.append(secret_volumemount)

    volumes.append(secret_volume)

    main_container = {
                    "name": container.label,
                    "command": ["/bin/bash", "-c", f"chmod a+x {container.image.command}; {container.image.command}"],                   
                    "image": container.image.name,
                    "volumeMounts": volume_mounts,
                    "ports": pod_ports,
                    "imagePullPolicy": CONTAINER_SETTINGS['kubernetes']['imagePullPolicy'],
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
#                "nodeSelector": container.target_node, 
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
        if json.loads(e.body)['code'] != 409: # already exists
            logger.critical(e)
    try:
        v1.create_namespaced_pod(namespace = namespace, body = pod_definition)
    except client.rest.ApiException as e:
        if json.loads(e.body)['code'] != 409: # already exists
            logger.critical(e)


def stop(container):
    logger.info(f"- stopping {container.label}")
    config.load_kube_config()
    v1 = client.CoreV1Api()
    try:
        msg = v1.delete_namespaced_pod(namespace = namespace, name = container.label)
    except client.rest.ApiException as e:
        if json.loads(e.body)['code'] != 404: # doesnt exists
            logger.error(e)
    try:
        msg = v1.delete_namespaced_service(namespace = namespace, name = container.label)
    except client.rest.ApiException as e:
        if json.loads(e.body)['code'] != 404: # doesnt exists
            logger.error(e)


