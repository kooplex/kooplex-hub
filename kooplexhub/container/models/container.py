import logging
import os
import datetime
import requests
import time

from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.html import format_html

#from .report import Report
from hub.models import Profile
from .image import Image
from .envvar import EnvVarMapping
from .proxy import Proxy

from kooplexhub.lib import  now
from kooplexhub.lib import my_alphanumeric_validator

try:
    from kooplexhub.settings import KOOPLEX
except ImportError:
    KOOPLEX = {}

logger = logging.getLogger(__name__)

class Container(models.Model):
    ST_NOTPRESENT = 'np'
    ST_STARTING = 'starting'
    ST_RUNNING = 'run'
    ST_NEED_RESTART = 'restart'
    ST_ERROR = 'oops'
    ST_STOPPING = 'stopping'
    ST_LOOKUP = {
        ST_NOTPRESENT: 'Not present.',
        ST_STARTING: 'Starting...',
        ST_RUNNING: 'Running fine.',
        ST_NEED_RESTART: 'Restart required',
        ST_ERROR: 'Error occured.',
        ST_STOPPING: 'Stopping...',
    }

    name = models.CharField(max_length = 200, null = False)
    label = models.CharField(max_length = 200, null = False, unique = True)
    user = models.ForeignKey(User, on_delete = models.CASCADE, null = False)
    image = models.ForeignKey(Image, on_delete = models.CASCADE, null = False)
    launched_at = models.DateTimeField(null = True, blank = True)
    start_teleport = models.BooleanField(default = False)
    start_ssh = models.BooleanField(default = False)
    start_seafile = models.BooleanField(default = False)

    require_running = models.BooleanField(default = False)
    state = models.CharField(max_length = 16, choices = ST_LOOKUP.items(), default = ST_NOTPRESENT)
    state_backend = models.CharField(max_length = 32, null = True, blank = True, default = None)
    state_lastcheck_at = models.DateTimeField(default = None, null = True, blank = True)

    restart_reasons = models.CharField(max_length = 500, null = True, blank = True)

    node = models.TextField(max_length = 64, null = True, blank = True)
    cpurequest = models.DecimalField(null = True, blank = True, decimal_places=1, max_digits=4, default=0.2)
    gpurequest = models.IntegerField(null = True, blank = True, default=0)
    memoryrequest = models.DecimalField( null = True, blank = True, decimal_places=1, max_digits=5, default=0.4)
    idletime = models.IntegerField( null = True, blank = True, default=28)

    class Meta:
        unique_together = [['user', 'name']]

    def __lt__(self, c):
        return self.launched_at < c.launched_at

    def __str__(self):
        return self.label

    @property
    def search(self):
        return self.name.upper()

    @property
    def link_drop(self):
        from django.urls import reverse
        return reverse('container:destroy', args = [self.id]) if self.id else ""

    def redirect(self, serviceview_id):
        from . import ServiceView ,ProxyImageBinding
        from kooplexhub.lib import custom_redirect
        #sv = ServiceView.objects.filter(id=serviceview_id, proxy__image=self.image).first()
        #FIXME: simplify ???
        sv = ServiceView.objects.filter(id=serviceview_id).first()
        if sv:
            b=ProxyImageBinding.objects.filter(image=self.image, proxy=sv.proxy).first()
            if not b:
                return reverse('container:list')
            url=sv.url_substitute(self)
            if sv.pass_token:
                return custom_redirect(url, token=self.user.profile.token)
            else:
                return custom_redirect(url)
        else:
            return reverse('container:list')


    @property
    def proxies(self):
        from . import ProxyImageBinding
        proxy_list = [ b.proxy for b in ProxyImageBinding.objects.filter(image=self.image) ]
        return proxy_list


    def addroutes(self):
        for proxy in self.proxies:
            proxy.addroute(self)


    def removeroutes(self):
        for proxy in self.proxies:
            proxy.removeroute(self)


    def views(self):
        views = {}
        for proxy in self.proxies:
            views.update(proxy.views)
        return [ v for v, o in views.items() if o ]


    #FIXME: deprecate
    #@property
    #def default_proxy(self):
    #    return Proxy.objects.get(image = self.image, default = True)

    #FIXME: deprecate
    #@property
    #def url_internal(self):
    #    return self.default_proxy.service_endpoint(self)

    #FIXME: deprecate
    #@property
    #def url_notebook(self):
    #    return self.default_proxy.url_notebook(self)

    #FIXME: deprecate
    #@property
    #def url_kernel(self):
    #    token="fsf"
    #    logger.info('Get %s' % (self.user))
    #    logger.info('Get %s' % (Profile.objects.get(user=self.user)))
    #    token = Profile.objects.get(user=self.user).token
    #    return self.default_proxy.url_container(self)+"?token="+token

    def env_variable(self, var_name):
        try:
            return EnvVarMapping.objects.get(image = self.image, name = var_name).valuemap
        except:
            return ""

    @property
    def env_variables(self):
        try:
            return [ {'name': envs.name, "value":envs.valuemap}  for envs in EnvVarMapping.objects.filter(image = self.image)]
        except:
            return {}


#FIXME: pl project app ha nincs istallálva, itt gondok lehetnek
    @property
    def projects(self):
        from project.models import ProjectContainerBinding
        return [ binding.project for binding in ProjectContainerBinding.objects.filter(container = self) ]

    @property
    def courses(self):
        from education.models import CourseContainerBinding
        return [ binding.course for binding in CourseContainerBinding.objects.filter(container = self) ]

#    @property
#    def reports(self):
#        "relevant only for report containers"
#        from report.models import ReportContainerBinding
#        return [ binding.report for binding in ReportContainerBinding.objects.filter(container = self) ]
    
    @property
    def target_node(self):
        return {'kubernetes.io/hostname': self.node} if self.node else KOOPLEX.get('kubernetes', {}).get('nodeSelector_k8s', {}) 

    @property
    def synced_libraries(self):
        return []
#FIXME:        from .filesync import FSLibraryContainerBinding
#FIXME:        return [ binding.fslibrary for binding in FSLibraryContainerBinding.objects.filter(service = self) ]

    @property
    def repos(self):
        return []
#FIXME:        from .versioncontrol import VCProjectContainerBinding
#FIXME:        return [ binding.vcproject for binding in VCProjectContainerBinding.objects.filter(service = self) ]

    @property
    def mount_cloud(self):
        mc = {'url' : 'https://seafile.vo.elte.hu/seafdav',
                'pw' :'vmi' }
        # Should iterate over the cloud service parameters
        envs = [
            {'name': "WEBDRIVE_USERNAME", "value": "seafile-email"}, 
            {'name': "WEBDRIVE_PASSWORD_FILE", "value": "/.davfssecrets/.davfs"}, 
            {'name': "WEBDRIVE_MOUNT", "value": "/v/cloud-seafile.vo.elte.hu"}, 
            {'name': "WEBDRIVE_URL", "value": "https://seafile.vo.elte.hu/seafdav"}, #FIXME Hardcoded
            {'name': "OWNER", "value": "1029"}, 
            ]
        return None

    @property
    def volumes(self):
        from volume.models import VolumeContainerBinding
        return [ binding.volume for binding in VolumeContainerBinding.objects.filter(container = self) ]

    def start(self):
        from ..tasks import start_container
        self.require_running=True
        start_container(self.user.id, self.id)

    def stop(self):
        from ..tasks import stop_container
        self.require_running=False
        self.restart_reasons=None
        self.save()
        self.removeroutes()
        stop_container(self.user.id, self.id)

    def restart(self):
        from ..tasks import stop_container
        self.require_running=True
        self.restart_reasons=None
        self.save()
        stop_container(self.user.id, self.id)

    def retrieve_log(self):
        from ..lib import fetch_containerlog
        return  fetch_containerlog(self)

    def mark_restart(self, reason, save = True):
        if self.state not in [ self.ST_RUNNING, self.ST_NEED_RESTART ]:
            return False
        if self.restart_reasons:
            self.restart_reasons += '; ' + reason
        else:
            self.restart_reasons = reason
        self.state = self.ST_NEED_RESTART
        if save:
            self.save()
        return True

    # rendering logic
    def render_name_html(self):
        return self.name #FIXME render_to_string("widgets/widget_container_start.html", {"container": self})

    def render_image_html(self):
        return render_to_string("widgets/widget_image.html", {"pk": self.id, "image": self.image})

    def render_start_html(self):
        return render_to_string("widgets/widget_container_start.html", {"container": self}) if self.id else ""

    def render_stop_html(self):
        return render_to_string("widgets/widget_container_stop.html", {"container": self}) if self.id else ""

    def render_open_html(self):
        return render_to_string("widgets/widget_container_views.html", {"container": self })

    def render_fetchlogs_html(self):
        _active = [ Container.ST_RUNNING, Container.ST_ERROR, Container.ST_NEED_RESTART ]
        return render_to_string("widgets/widget_container_fetchlogs.html", {"container": self, "is_active": self.state in _active}) if self.id else ""

    def render_state_html(self):
        return render_to_string("widgets/widget_container_state.html", {"container": self}) if self.id else ""

    def render_restartreasons_html(self):
        return render_to_string("widgets/widget_container_restartreasons.html", {"container": self}) if self.id else ""
