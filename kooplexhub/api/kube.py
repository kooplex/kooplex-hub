#FIXME: place in lib/kubernetes.py
# try merge code overlaps

from kubernetes import config
from kubernetes.client import *
import logging
import json

logger = logging.getLogger(__name__)



def submit_job(cnf):
    # , node):
    username = cnf.get('username')
    env_variables = [
        { "name": "LANG", "value": "en_US.UTF-8" },
        { "name": "USER", "value": username },
    ]
    volume_mounts = [
            V1VolumeMount(name="nslcd", mount_path='/etc/mnt'),
            V1VolumeMount(name="initscripts", mount_path="/init")
            ]
    volumes = [V1Volume(name="nslcd", config_map=V1ConfigMapVolumeSource(name="nslcd", default_mode=420, items=[
            V1KeyToPath(key="nslcd", path='nslcd.conf')])),
            V1Volume(name="initscripts", config_map=V1ConfigMapVolumeSource(name="initscripts", default_mode=0o777, items=[
            V1KeyToPath(key="nslcd",path="initscripts")]))
            ]


    if cnf.get('home_rw', None) is not None:
        volume_mounts.append(
        V1VolumeMount(name="home", mount_path= f'/v/{username}', sub_path=username))
        volumes.append(V1Volume(name="home",persistent_volume_claim = V1PersistentVolumeClaimVolumeSource(claim_name= "home", read_only=not cnf.get('home_rw'))))

    if cnf.get('scratch'):
        volume_mounts.append(
        V1VolumeMount(name="scratch", mount_path= f'/v/scratch/', sub_path=username))
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
        
    resources = V1ResourceRequirements(limits={
                            "nvidia.com/gpu": cnf.get('gpu'),
                            "cpu": cnf.get('cpu'),
                            "memory": cnf.get('memory'),
                            },
                        requests={
                            "nvidia.com/gpu": cnf.get('gpu'),
                            "cpu": cnf.get('cpu'),
                            "memory": cnf.get('memory'),
                            }
                        )

    meta = V1ObjectMeta(name = cnf.get('name'), namespace = cnf.get('namespace'), labels = {"krftjobs":"true"}) #FIXME

    template = V1PodTemplateSpec()
    template.spec = V1PodSpec(containers=[
           V1Container(name=cnf.get('name'), image=cnf.get('image'), command=["/bin/bash", "-c", f"/init/initscripts; {cnf.get('command')}" ],
                volume_mounts=volume_mounts, image_pull_policy="IfNotPresent", env=env_variables,
                resources=resources)
        ], restart_policy="Never", volumes=volumes)

    if cnf.get('node'):
        template.spec.node_name = node_name
    else:
        template.spec.node_selector = { cnf.get('nodeselector', "default"): "true" }
    spec = V1JobSpec(template=template, ttl_seconds_after_finished=72000)
    spec.parallelism = cnf.get('parallelism')
    spec.completions = cnf.get('completions')
    spec.completion_mode = "Indexed"

    config.load_kube_config()
    v1 = BatchV1Api()

    data = V1Job(api_version = 'batch/v1', kind = 'Job', metadata = meta, spec = spec)

    try:
        return v1.create_namespaced_job(namespace = cnf.get('namespace'), body = data)
    except rest.ApiException as e:
        logger.warning(e)
        oops = json.loads(e.body)
        logger.debug(data)
        return { "Error": oops['code'], "message": oops['message'] }

