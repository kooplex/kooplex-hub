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
    def link_drop(self):
        from django.urls import reverse
        return reverse('container:destroy', args = [self.id]) if self else ""

    @property
    def default_proxy(self):
        return Proxy.objects.get(image = self.image, default = True)

    @property
    def proxy_route(self):
        return self.default_proxy.proxy_route(self)

    @property
    def url_internal(self):
        return self.default_proxy.url_internal(self)

    @property
    def url_notebook(self):
        return self.default_proxy.url_notebook(self)

    @property
    def url_kernel(self):
        token="fsf"
        logger.info('Get %s' % (self.user))
        logger.info('Get %s' % (Profile.objects.get(user=self.user)))
        token = Profile.objects.get(user=self.user).token
        return self.default_proxy.url_container(self)+"?token="+token

    @property
    def search(self):
        return self.name.upper()

    #DEPRECATE
    def wait_until_ready(self):
        from kooplexhub.lib import keeptrying
        for _ in range(5):
            resp = keeptrying(method = requests.get, times = 5, url = self.url_notebook, timeout = .05, allow_redirects = False)
            logger.info('Get %s -> [%d]' % (self.url_notebook, resp.status_code))
            time.sleep(.1)
            if resp.status_code != 503:
                return resp
            logger.warning('Proxy target missing: %s' % self.url_notebook)

    def env_variable(self, var_name):
        try:
            return EnvVarMapping.objects.get(image = self.image, name = var_name).valuemap
        except:
            return ""

    @property
    def proxies(self):
        from .proxy import Proxy
        return list(Proxy.objects.filter(image = self.image))

#FIXME: pl project app ha nincs istallálva, itt gondok lehetnek
    @property
    def projects(self):
        from project.models import ProjectContainerBinding
        return [ binding.project for binding in ProjectContainerBinding.objects.filter(container = self) ]

    @property
    def courses(self):
        from education.models import CourseContainerBinding
        return [ binding.course for binding in CourseContainerBinding.objects.filter(container = self) ]

    @property
    def reports(self):
        "relevant only for report containers"
        from report.models import ReportContainerBinding
        return [ binding.report for binding in ReportContainerBinding.objects.filter(container = self) ]
    
    @property
    def target_node(self):
        return {'kubernetes.io/hostname': self.node} if self.node else KOOPLEX['kubernetes'].get('nodeSelector_k8s') 

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

    @property
    def mapped_backend_state(self):
        from ..lib import state_mapper
        return state_mapper.get(self.state_backend,  self.ST_NOTPRESENT)

    def start(self):
        from ..tasks import start_container
        self.check_state()
        if self.mapped_backend_state!=self.ST_NOTPRESENT:
            logger.warning(f"Not starting {self} because {self.state} {self.mapped_backend_state}")
            return
        self.state = self.ST_STARTING
        self.restart_reasons = None
        self.save()
        start_container(self.user.id, self.id)

    def stop(self):
        from ..tasks import stop_container
        self.check_state()
        if self.mapped_backend_state not in [self.ST_RUNNING, self.ST_ERROR]:
            logger.warning(f"Not stopping {self} because {self.state} and {self.mapped_backend_state}")
            return
        self.state = self.ST_STOPPING
        self.restart_reasons = None
        self.save()
        return stop_container(self.user.id, self.id)

    def restart(self):
        from ..tasks import restart_container
        self.check_state()
        if self.mapped_backend_state not in [self.ST_RUNNING, self.ST_ERROR]:
            logger.warning(f"Not restarting {self} because {self.state} and {self.mapped_backend_state}")
            return
        self.restart_reasons = None
        self.state = self.ST_STOPPING
        self.save()
        return restart_container(self.user.id, self.id)

    def check_state(self, retrieve_log = False):
        from ..lib import check_environment, fetch_containerlog
        from ..lib import state_mapper
        state = check_environment(self)
        if retrieve_log:
            state['podlog'] = fetch_containerlog(self)
        mapped_state=self.mapped_backend_state
        if self.state==self.ST_RUNNING and state_mapper.get(state.get('pod_phase'))==self.ST_NOTPRESENT:
            self.state=self.ST_NOTPRESENT
            self.save()
        elif self.state in [self.ST_STARTING, self.ST_STOPPING] and mapped_state in [self.ST_NOTPRESENT, self.ST_RUNNING, self.ST_ERROR]:
            self.state=mapped_state
            self.save()
        elif self.state==self.ST_ERROR and mapped_state==self.ST_NOTPRESENT:
            self.state=self.ST_NOTPRESENT
            self.save()
        elif self.state==self.ST_NOTPRESENT and state_mapper.get(state.get('pod_phase'))==self.ST_RUNNING:
            self.state=self.ST_RUNNING
            self.save()
        return state

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
        return render_to_string("widgets/widget_container_start.html", {"container": self})

    def render_stop_html(self):
        return render_to_string("widgets/widget_container_stop.html", {"container": self})

    def render_open_html(self):
        _link = reverse('container:open', args = [self.id]) if self.id else ""
        return render_to_string("widgets/widget_container_open.html", {"container": self, "link": _link})

    def render_fetchlogs_html(self):
        _active = [ Container.ST_RUNNING, Container.ST_ERROR ]
        return render_to_string("widgets/widget_container_fetchlogs.html", {"container": self, "is_active": self.mapped_backend_state in _active})

    def render_state_html(self):
        return render_to_string("widgets/widget_container_state.html", {"container": self})

    def render_restartreasons_html(self):
        return render_to_string("widgets/widget_container_restartreasons.html", {"container": self})
