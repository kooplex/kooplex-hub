import json
import logging

from django.shortcuts import render
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt

from container.models import Image
from project.models import UserProjectBinding
from volume.models import UserVolumeBinding, Volume
from container.lib import Cluster

from kubernetes import client, config
from kubernetes.client import *

logger = logging.getLogger(__name__)

#FIXME:
from api.kube import submit_job, delete_job, info_job, get_jobs, log_job

@require_http_methods(["GET"])
def version(request):
    return JsonResponse({
        'version': '0.1',
        'now': timezone.now(),
    })

@login_required
@require_http_methods(["GET"])
def images(request):
    return JsonResponse({ 
        'images': [ i.name for i in Image.objects.filter(imagetype = Image.TP_PROJECT, present = True) ],
    })

@login_required
@require_http_methods(["GET"])
def projects(request):
    return JsonResponse({ 
        'projects': [ { 'id': b.project.id, 'name': b.project.name } for b in UserProjectBinding.objects.filter(user = request.user) ],
    })

@login_required
@require_http_methods(["GET"])
def volumes(request):
    shared = Q(user = request.user, volume__scope__in = [ Volume.SCP_PRIVATE, Volume.SCP_INTERNAL ])
    public = Q(volume__scope = Volume.SCP_PUBLIC)
    return JsonResponse({ 
        'volumes': [ { 'id': b.volume.id, 'folder': b.volume.folder } for b in UserVolumeBinding.objects.filter(shared | public).filter(volume__is_present = True) ],
        'attachments': [ { 'id': v.id, 'folder': v.folder } for v in Volume.objects.filter(scope = Volume.SCP_ATTACHMENT, is_present = True) ],
    })

@login_required
@require_http_methods(["GET"])
def nodes(request):
    api = Cluster()
    api.query_nodes_status(reset=True)#FIXME
    api.query_pods_status(reset=True)
    api.resources_summary()
    return JsonResponse( api.get_data_transpose() )

@login_required
@require_http_methods(["GET"])
def jobs(request):
    return JsonResponse({ 
        'jobs': get_jobs('k8plex-test-jobs', request.user.username), #FIXME: ns
    })

@csrf_exempt
@login_required
@require_http_methods(["POST"])
def submit(request, job_name):
    req = json.loads(request.POST.get("job_description", "{}"))
    name = req.get('name')
    if (name != job_name) or (request.user.username != request.COOKIES.get('api_user', None)):
        return JsonResponse({
            'job_description': req,
            'api_response': { "Error": 1, "message": "Inconsistent parameters" },
        })

    home_rw = req.get('home_rw', None)
    if home_rw:
        home_rw = bool(home_rw)

    req_parsed = dict(
        namespace = req.get("namespace"),
        name = name, 
        image = req.get('image'),
        username = request.user.username, 
        home_rw = home_rw,
        scratch = bool(req.get("scratch", False)),
        gpu = int(req.get("gpu", 0)),
        cpu = float(req.get("cpu", 1)),
        memory = req.get("memory", "2G"),
        command = req.get("command"),
        parallelism = int(req.get("parallelism", 1)),
        completions = int(req.get("completions", 1)),
        node = req.get("nodename", None),
    )

    auth_project = lambda p_ids: set([ b.project.subpath for b in UserProjectBinding.objects.filter(user = request.user, project__id__in = p_ids) ])

    shared = Q(user = request.user, volume__scope__in = [ Volume.SCP_PRIVATE, Volume.SCP_INTERNAL ])
    public = Q(volume__scope = Volume.SCP_PUBLIC)
    volumes = { b.volume.id: b.volume.folder for b in UserVolumeBinding.objects.filter(shared | public).filter(volume__is_present = True) }
    attachments = { v.id: v.folder for v in Volume.objects.filter(scope = Volume.SCP_ATTACHMENT, is_present = True) }
    auth_volume = lambda v_ids: set([ volumes[v_id] for v_id in v_ids if v_id in volumes ])
    auth_attachment = lambda v_ids: set([ attachments[v_id] for v_id in v_ids if v_id in attachments ])

    req_parsed.update(dict(
        projects_ro = list(auth_project(req.get("projects_ro", []))),
        projects_rw = list(auth_project(req.get("projects_rw", [])).difference(auth_project(req.get("projects_ro", [])))),
        volumes_ro = list(auth_volume(req.get("volumes_ro", []))),
        volumes_rw = list(auth_volume(req.get("volumes_rw", [])).difference(auth_volume(req.get("volumes_ro", [])))),
        attachments_ro = list(auth_attachment(req.get("volumes_ro", []))),
        attachments_rw = list(auth_attachment(req.get("volumes_rw", [])).difference(auth_attachment(req.get("volumes_ro", [])))),
    ))

    try:
        api_resp = submit_job(req_parsed)
    except Exception as e:
        api_resp = str(e)
    return JsonResponse({
        'job_description': req,
        'job_description_parsed': req_parsed,
        'api_response': api_resp,
    })


@login_required
@require_http_methods(["GET"])
def info(request, job_name):
    namespace = 'k8plex-test-jobs' #FIXME: req.get("namespace"),
    label = job_name
    user = request.user
    api_resp = info_job(namespace, user.username, label)
    return JsonResponse({ 'api_response': api_resp })

@login_required
def log(request, job_name):
    namespace = 'k8plex-test-jobs' #FIXME: req.get("namespace"),
    api_resp = log_job(namespace, request.user.username, job_name)
    return JsonResponse({ 'api_response': api_resp })

@csrf_exempt
@login_required
@require_http_methods(["DELETE"])
def delete(request, job_name):
    namespace = 'k8plex-test-jobs' #FIXME: req.get("namespace"),
    label = job_name
    user = request.user
    try:
        api_resp = delete_job(namespace, user.username, label)
    except Exception as e:
        api_resp = str(e)
    return JsonResponse({ 'api_response': api_resp })


