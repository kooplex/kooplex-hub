import json, os
import logging
import yaml

from django.shortcuts import render
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt

from container.models import Image, Proxy, EnvVarMapping, ProxyImageBinding, ServiceView
from project.models import UserProjectBinding
from volume.models import UserVolumeBinding, Volume
from container.lib import Cluster

from api.kube import submit_job, delete_job, info_job, get_jobs, log_job

logger = logging.getLogger(__name__)

from container.conf import CONTAINER_SETTINGS
NS_JOBS = CONTAINER_SETTINGS['kubernetes']['jobs']['namespace']

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
        'images': [ i.name for i in Image.objects.filter(imagetype = Image.ImageType.PROJECT, present = True) ],
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
    shared = Q(user = request.user, volume__scope__in = [ Volume.Scope.PRIVATE, Volume.Scope.INTERNAL ])
    public = Q(volume__scope = Volume.Scope.PUBLIC)
    return JsonResponse({ 
        'volumes': [ { 'id': b.volume.id, 'folder': b.volume.folder } for b in UserVolumeBinding.objects.filter(shared | public).filter(volume__is_present = True) ],
        'attachments': [ { 'id': v.id, 'folder': v.folder } for v in Volume.objects.filter(scope = Volume.Scope.ATTACHMENT, is_present = True) ],
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
        'jobs': get_jobs(NS_JOBS, request.user.username),
    })

@csrf_exempt
@login_required
@require_http_methods(["POST"])
def submit(request, job_name):
    req = json.loads(request.POST.get("job_description", "{}"))
    name = req.get('name')
    if (name != job_name) or (request.user.username != request.COOKIES.get('api_user', None)):
        return JsonResponse({
            'Error': 1, 
            'message': 'Inconsistent parameters',
            'description': req,
        })

    home_rw = req.get('home_rw', None)
    if home_rw:
        home_rw = bool(home_rw)

    req_parsed = dict(
        namespace = NS_JOBS,
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

    shared = Q(user = request.user, volume__scope__in = [ Volume.Scope.PRIVATE, Volume.Scope.INTERNAL ])
    public = Q(volume__scope = Volume.Scope.PUBLIC)
    volumes = { b.volume.id: b.volume for b in UserVolumeBinding.objects.filter(shared | public).filter(volume__is_present = True) }
    attachments = { v.id: v.folder for v in Volume.objects.filter(scope = Volume.Scope.ATTACHMENT, is_present = True) }
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

    api_resp = submit_job(req_parsed)
    #So that it becomes JsonSerializable
    api_resp['job_description']['volumes_ro'] = [v.folder for v in api_resp['job_description']['volumes_ro']]
    api_resp['job_description']['volumes_rw'] = [v.folder for v in api_resp['job_description']['volumes_rw']]
    return JsonResponse(api_resp)


@login_required
@require_http_methods(["GET"])
def info(request, job_name):
    api_resp = info_job(NS_JOBS, request.user.username, job_name)
    return JsonResponse(api_resp)

@login_required
def log(request, job_name):
    api_resp = log_job(NS_JOBS, request.user.username, job_name)
    return JsonResponse({ 'container_logs': api_resp })

@csrf_exempt
@login_required
@require_http_methods(["DELETE"])
def delete(request, job_name):
    api_resp = delete_job(NS_JOBS, request.user.username, job_name)
    return JsonResponse(api_resp)
 

@csrf_exempt
@login_required
@require_http_methods(["POST"])
def install_image(request, image_path):
    modify=True
    notmodified=True
    # Example: Read and process YAML file in the request
    uploaded_file = request.FILES.get("file")
    logger.debug(dir(request))
    logger.debug(image_path)
    if not uploaded_file:
        return JsonResponse({"error1": "No file uploaded"})

    # Read YAML content
    yaml_content = uploaded_file.read().decode("utf-8")
    logger.debug(yaml_content)
    yaml_data = yaml.safe_load(yaml_content)

    try:
        with open('/tmp/output.yaml', 'w') as outfile:
            yaml.dump(yaml_data, outfile, default_flow_style=False)
        # Process YAML data, for instance, save to the database
        # This depends on the structure of your YAML data
        #logger.debug(f"{yaml_data['name']}, {yaml_data['description']}")
        from container.models import Image
        from hub.models import Thumbnail

        for items in yaml_data:
            image = items.get('image', {})
            if image:
              image_registry = image.pop('registry')
              image_name = os.path.join(image_registry, image_path)
              instance = Image.objects.filter(name=image_name).first()
              if instance:
                  if modify:
                      instance.name = image_name
                      instance.description=image.get('description', '')
                          # Make sure that imagetype is set to Image.ImageType.?
                      instance.imagetype=image.pop('imagetype', Image.ImageType.PROJECT),
                      instance.present=image.pop('present', True)
                      instance.dockerfile=image.pop('dockerfile', '')
                      instance.command=image.pop('command', '/entrypoint.sh')
                      instance.thumbnail=Thumbnail.objects.get(name=image.pop('thumbnail', 'jupyter')) #FIXME let it be default not jupyter!
                      instance.description = "\n".join([f"{key}: {image[key]}" for key in image.keys()])
                  else:
                      logger.info(f"Image {image_name} is already installed")
                      return JsonResponse({"message": f"Image {image_name} is already installed"})        
              else:
                  instance = Image.objects.create(
                      name=image_name,
                      description="",
                      # Make sure that imagetype is set to Image.ImageType.?
                      imagetype=image.pop('imagetype', Image.ImageType.PROJECT),
                      present=image.pop('present', True),
                      dockerfile=image.pop('dockerfile', ''),
                      command=image.pop('command', '/entrypoint.sh'),
                      thumbnail=Thumbnail.objects.get(name=image.pop('thumbnail', 'jupyter')) #FIXME let it be default not jupyter!
                  )
                  instance.description = "\n".join([f"{key}: {image[key]}" for key in image.keys()])
                  instance.save()
                  logger.info(f"Image {image_name} is installed")
                  notmodified = False

            # Proxy settings
            proxy_settings = image.get('proxy', {})
            logger.debug(f"Proxy settings for {image_name}: {proxy_settings}")
            if proxy_settings:
              for psk in proxy_settings.keys():
                  ps = proxy_settings[psk]
                  ps['name']=psk
                  try:
                    po, ex = Proxy.objects.get_or_create(**ps)
                    pib = ProxyImageBinding.objects.get_or_create(proxy=po, image=instance)
                  except Exception as e:
                      logger.error(f"Proxy settings error: {e}")
                      
            sv_settings = image.get('service_view', {})
            logger.debug(f"Servce view settings for {image_name}: {sv_settings}")
            if sv_settings:
              for svk in sv_settings.keys():
                  sv = sv_settings[svk]
                  sv['name']= svk
                  try:
                    po = Proxy.objects.get(name=sv['proxy'])
                    sv['proxy']=po
                    icon = Thumbnail.objects.get(name=sv['icon'])
                    sv['icon']=icon
                    svo, ex = ServiceView.objects.get_or_create(**sv)
                  except Exception as e:
                      logger.error(f"Service View settings error: {e}")

            if notmodified:
                return JsonResponse({"message": f"Image {image_name} is succesfully installed"})        
            else:
                return JsonResponse({"message": f"Image {image_name} is modified"}) 
            
    except Exception as e:
        logger.error(str(e))
        return JsonResponse({"error2": str(e)})
