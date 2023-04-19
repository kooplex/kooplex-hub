#FIXME: place in lib/kubernetes.py
# try merge code overlaps

from kubernetes import config
from kubernetes.client import *
import logging
import json
import base64

logger = logging.getLogger(__name__)

from kooplexhub.settings import KOOPLEX

kube = KOOPLEX.get('kubernetes', {})

config.load_kube_config(kube.get('kubeconfig_job', '/root/.kube/config'))
api_batch = BatchV1Api()
api_core = CoreV1Api()


def _job_pods(namespace, user, label):
    for pod in api_core.list_namespaced_pod(namespace = namespace).items:
        if pod.metadata.labels['job-name'] != label:
            continue
        for c in pod.spec.containers:
            for e in c.env:
                if e.name == 'USER' and e.value == user:
                    yield pod
                    break
            else:
                continue
            break


def submit_job(cnf):
    username = cnf.get('username')
    env_variables = [
        { "name": "LANG", "value": "en_US.UTF-8" },
        { "name": "USER", "value": username },
            #'SSH_AUTH_SOCK': '/tmp/{container.user.username}', #FIXME: move to db
    ]
    initscripts = [
        V1KeyToPath(key="nsswitch",path="01-nsswitch"),
        V1KeyToPath(key="nslcd",path="02-nslcd"),
    #        V1KeyToPath(key="usermod",path="03-usermod"),
    #        V1KeyToPath(key="munge",path="04-munge"),
    #        V1KeyToPath(key="ssh",path="05-ssh"),
            ]
    volumes = [
        V1Volume(name="nslcd", config_map=V1ConfigMapVolumeSource(name="nslcd", default_mode=420, items=[V1KeyToPath(key="nslcd", path='nslcd.conf')])),
        V1Volume(name="initscripts", config_map=V1ConfigMapVolumeSource(name="initscripts", default_mode=0o777, items=initscripts ))
    ]
    volume_mounts = [
        V1VolumeMount(name="nslcd", mount_path='/etc/mnt'),
        V1VolumeMount(name="initscripts", mount_path="/.init_scripts")
    ]


    #if container.user.profile.can_teleport:
    #    initscripts.append(V1KeyToPath(key="teleport",path="06-teleport"))
    #    env_variables.append({ "name": "REDIS_PASSWORD", "value": REDIS_PASSWORD })


    #if container.start_ssh:
    #    initscripts.append(V1KeyToPath(key="sshstart",path="07-sshstart"))
    #    sshport = 2222
    #    pod_ports.append({
    #        "containerPort": 22,
    #        "name": "ssh", 
    #    })
    #    svc_ports.append({
    #        "port": sshport,
    #        "targetPort": 22,
    #        "protocol": "TCP",
    #        "name": "ssh", 
    #    })


    if cnf.get('home_rw', None) is not None:
        volume_mounts.append(V1VolumeMount(name="home", mount_path= f'/v/{username}', sub_path=username))
        volumes.append(V1Volume(name="home",persistent_volume_claim = V1PersistentVolumeClaimVolumeSource(claim_name= "home", read_only=not cnf.get('home_rw'))))

    if cnf.get('scratch'):
        volume_mounts.append(V1VolumeMount(name="scratch", mount_path= f'/v/scratch/', sub_path=username))
        volumes.append(V1Volume(name="scratch",persistent_volume_claim = V1PersistentVolumeClaimVolumeSource(claim_name= "scratch")))

    mnt_p = False
    for ps, ro in zip([cnf.get('projects_rw'), cnf.get('projects_ro')], [False, True]):
        for p in ps:
            mnt_p = True
            volume_mounts.append({
                "name": "project",
                "mountPath": f'/v/projects/{p}',
                "subPath": f'projects/{p}',
            })
        if mnt_p:
            volumes.append(V1Volume(name="project",persistent_volume_claim = V1PersistentVolumeClaimVolumeSource(claim_name= "project", read_only=ro)))

    mnt_a = False
    for As, ro in zip([cnf.get('attachments_rw'), cnf.get('attachments_ro')], [False, True]):
        for a in As:
            mnt_a = True
            volume_mounts.append({
                "name": "attachments",
                "mountPath": f'/v/attachments/{a}',
                "subPath": f'{a}',
            })
        if mnt_a:
            volumes.append(V1Volume(name="attachments",persistent_volume_claim = V1PersistentVolumeClaimVolumeSource(claim_name= "attachments", read_only=ro)))

    mnt_v = False
    for vs, ro in zip([cnf.get('volumes_rw'), cnf.get('volumes_ro')], [False, True]):
        for v in vs:
            mnt_v = True
            volume_mounts.append({
                "name": f"v-{v}",
                "name": f"v-{v}",
                "mountPath": f'/v/volumes/{v}',
            })
        if mnt_v:
            volumes.append(V1Volume(name=f"v-{v}",persistent_volume_claim = V1PersistentVolumeClaimVolumeSource(claim_name= v, read_only=ro)))
        
    resources = V1ResourceRequirements(
        limits = {
            "nvidia.com/gpu": cnf.get('gpu'),
            "cpu": cnf.get('cpu'),
            "memory": cnf.get('memory'),
        },
        requests = {
            "nvidia.com/gpu": cnf.get('gpu'),
            "cpu": cnf.get('cpu'),
            "memory": cnf.get('memory'),
        }
    )

    meta = V1ObjectMeta(name = cnf.get('name'), namespace = cnf.get('namespace'), labels = {"krftjobs":"true"}) #FIXME

    template = V1PodTemplateSpec()
    template.spec = V1PodSpec(
        containers = [
           V1Container(
               name=cnf.get('name'), image=cnf.get('image'),
               #FIXME:command=["/bin/bash", "-c", f"/init/initscripts; {cnf.get('command')}" ],
               # image.command
               command=["/bin/bash", "-c", f"/entrypoint.sh || {cnf.get('command')}" ],
               #command=["/bin/bash", "-c", "sleep infinity" ],
               #FIXME: vegyük ki az entrypoint végét initscriptbe?
               volume_mounts=volume_mounts, image_pull_policy="IfNotPresent", env=env_variables,
               resources=resources
            )
        ], 
        restart_policy="Never", volumes=volumes
    )

    if cnf.get('node'):
        template.spec.node_name = node_name
    else:
        template.spec.node_selector = { cnf.get('nodeselector', "default"): "true" }
    spec = V1JobSpec(template=template, ttl_seconds_after_finished=72000)
    spec.parallelism = cnf.get('parallelism')
    spec.completions = cnf.get('completions')
    spec.completion_mode = "Indexed"

    data = V1Job(api_version = 'batch/v1', kind = 'Job', metadata = meta, spec = spec)

    try:
        api_resp = api_batch.create_namespaced_job(namespace = cnf.get('namespace'), body = data)
        return { "Created": api_resp.metadata.creation_timestamp, "status": api_resp.status.to_dict() }
    except rest.ApiException as e:
        logger.warning(e)
        oops = json.loads(e.body)
        logger.debug(data)
        return { "Error": oops['code'], "message": oops['message'] }


def delete_job(namespace, user, label):
    job_description = api_batch.read_namespaced_job(namespace = namespace, name = label)
    try:
        for e in job_description.spec.template.spec.containers[0].env:
            if e.name == 'USER' and e.value == user:
                api_resp = api_batch.delete_namespaced_job(namespace = namespace, name = label, propagation_policy = 'Foreground')
                return {'response': 'ok'}
        return {'ERROR': 'not found' }
    except Exception as e:
        logger.error(f'{e} -- {api_resp}')
        return {}

def get_jobs(namespace, user):
    jobs = []
    for j in api_batch.list_namespaced_job(namespace = namespace).items:
        for e in j.spec.template.spec.containers[0].env:
            if e.name == 'USER' and e.value == user:
                name = j.metadata.name
                status = { a: getattr(j.status, a) for a in [ 'active', 'ready', 'failed' ] }

                jobs.append({
                    'name': name,
                    'status': status,
                })
                break
    return jobs


def info_job(namespace, user, label):
    container_attrs2show = [ 'command', 'image', 'name', 'resources' ]
    try:
        pods = api_core.list_namespaced_pod(namespace = namespace)
        match = lambda x: x.metadata.labels['job-name'] == label
        pcm = set.union( *[ set([ c.message for c in p.status.conditions ]) for p in filter(match, pods.items) ] )
        not_none = lambda x:x

        job_description = api_batch.read_namespaced_job(namespace = namespace, name = label)
        status = job_description.status
        
        return { 
            'name': job_description.metadata.name, 
            'containers': [ { k:v for k,v in c.to_dict().items() if k in container_attrs2show } for c in job_description.spec.template.spec.containers ],
            'status': status.to_dict(),
            'pod_condition_messages': list(filter(not_none, pcm)),
        }
    except rest.ApiException as e:
        logger.warning(e)
        oops = json.loads(e.body)
        return { "Error": oops['code'], "message": oops['message'] }

def log_job(namespace, user, label):
    logs = []
    for pod in _job_pods(namespace, user, label):
        try:
            logs.append(api_core.read_namespaced_pod_log(namespace = namespace, name = pod.metadata.name))
        except Exception as e:
            logs.append(f'ERROR retrieving log -- {e}')
    return logs


def save_token(namespace, user, token):
    config.load_kube_config(kube.get('kubeconfig', '/root/.kube/config'))
    api_core = CoreV1Api()
    token_store = KOOPLEX.get('kubernetes', {}).get('job_tokens', 'job-tokens')
    secrets = api_core.read_namespaced_secret(namespace=namespace, name=token_store)
    secrets.data[user] = base64.b64encode(token.encode()).decode()
    api_core.replace_namespaced_secret(namespace=namespace, name=token_store, body=secrets)
