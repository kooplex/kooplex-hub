import logging
import os

from django.db import transaction
from django.db import models
from django.conf.urls import url
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import redirect, render
from django_tables2 import RequestConfig
from django.views.generic import ListView, CreateView, UpdateView
from django.urls import reverse_lazy

from hub.models import Image
from hub.models import Report, Volume

from hub.forms import table_listvolume, FormVolume

from kooplex.lib import now, translate_date
from kooplex.settings import KOOPLEX
#from kooplex.lib.filesystem import mkdir_volume

logger = logging.getLogger(__name__)

def mkdir_volume(*v, **kw):
    pass

@login_required
def new_volume(request):#, next_page):
    """Renders new volume form."""
    user = request.user
    logger.debug("user %s, method: %s" % (user, request.method))
    if request.method == 'GET':
        context_dict = {
            'f_volume': FormVolume(user = user),
            'menu_volume': 'active',
            'next_page': 'indexpage', #next_page,
        }
        return render(request, 'volume/new.html', context = context_dict)
    elif request.method == 'POST' and request.POST['button'] == 'apply':
        dockerconf = KOOPLEX.get('docker', {})
        try:
            volumetype = request.POST['volumetype']
            displayname = request.POST['displayname']
                    ## FIXME
            if volumetype == Volume.FUNCTIONAL:
                name = "vol-" + displayname
            volume_dir = None #os.path.join(dockerconf.get('volume_dir', ''), name)
            if volume_dir:
                mkdir_volume(volume_dir, user)
            Volume.objects.create(
                name = name,
                displayname = displayname,
                description = request.POST['description'], 
                volumetype = volumetype,
            )
            messages.info(request, "volume %s is created" % request.POST['displayname'])
            return redirect('volume:list')
        except Exception as e:
            logger.error(e)
            raise
    else:
        return redirect('indexpage')

#@login_required
def list_volumes(request, files = []):#, next_page):
    """Renders new volume list."""
    user = request.user
    logger.debug("user %s, method: %s" % (user, request.method))
    if (request.method == 'POST' and request.POST.get('button', 'search') == 'search') or request.method == 'GET':
        pattern = request.POST.get('name', '')
        volumes = filter_volumes(user, pattern)
        #table = table_collaboration(project)
        #table_collaborators = table(user.profile.everybodyelse) if pattern == '' else table(user.profile.everybodyelse_like(pattern))
    elif request.method == 'POST' and request.POST.get('button') == 'showall':
        volumes = filter_volumes(user)
    else:
        volumes = filter_volumes(user)

    context_dict = {
        'menu_volume': 'active',
        'next_page': 'indexpage', #next_page,
        'volume_cats' : volumes,
        't_volumes_fun': table_listvolume(user, volumetype='functional'),
        't_volumes_stg': table_listvolume(user, volumetype='storage'),
        'files' : files,
    }
    return render(request, 'volume/list.html', context = context_dict)

#FIXME https://django-taggit.readthedocs.io/en/latest/getting_started.html
def filter_volumes(user, pattern = ''):
    if pattern:
        query_volumes = Volume.objects.filter(models.Q(description__icontains = pattern) | models.Q(name__icontains = pattern) )
    else:
        query_volumes = Volume.objects.all()
        
    return query_volumes

@login_required
def delete_volume(request, volume_id):
    user = request.user
    logger.debug("user %s, method: %s" % (user, request.method))
    try:
        volume = Report.objects.get(id = volume_id, creator = user)
        volume.delete()
        messages.info(request, "Deleted your volume: %s" % volume)
    except Exception as e:
        logger.warning('Cannot remove volume id: %s -- %s' % (volume_id, e))
        messages.warning(request, "Cannot delete requested volume.")
    return redirect('volume:list')



urlpatterns = [
    url(r'^newvolume/?$', new_volume, name = 'new'),
    url(r'^listvolumes/?$', list_volumes, name = 'list'),
    url(r'^filter_volumes/?$', list_volumes, name = 'filter_volumes'),
    url(r'^deletevolume/(?P<volume_id>\d+)$', delete_volume, name = 'delete'), 


 ]
