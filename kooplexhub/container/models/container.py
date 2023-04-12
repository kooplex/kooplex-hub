import logging
import os
import datetime
import requests
import time

from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User

#from .report import Report
from .image import Image
from .envvar import EnvVarMapping
from .proxy import Proxy

from kooplexhub.lib import  now
from kooplexhub.lib import my_alphanumeric_validator
from ..lib import start_environment, stop_environment, restart_environment, check_environment, fetch_containerlog

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

    state = models.CharField(max_length = 16, choices = ST_LOOKUP.items(), default = ST_NOTPRESENT)
    restart_reasons = models.CharField(max_length = 500, null = True, blank = True)
    state_lastcheck_at = models.DateTimeField(default = None, null = True, blank = True)

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
    def search(self):
        return self.name.upper()

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

#    @property
#    def env_variables(self):
#        for envmap in EnvVarMapping.objects.filter(image = self.image):
#            yield { "name": envmap.name, "value": envmap.valuemap.format(container = self) }

#    @property
#    def uptime(self):
#        timenow = now()
#        delta = timenow - self.launched_at
#        return delta if self.is_running else -1 #FIXME: ez nem mukodhet nincs ilyen attributum

    @property
    def proxies(self):
        from .proxy import Proxy
        return list(Proxy.objects.filter(image = self.image))

    @property
    def projects(self):
        from project.models import ProjectContainerBinding
        return [ binding.project for binding in ProjectContainerBinding.objects.filter(container = self) ]

    @property
    def courses(self):
        from education.models import CourseContainerBinding
        return [ binding.course for binding in CourseContainerBinding.objects.filter(container = self) ]

    @property
    def reports_bb(self):
        "relevant only for project containers"
        ##This is elegant but is buggy in current django version! update() also sucks
        ##reports = Report.objects.none()
        ##for p in self.projects:
        ##    reports = reports.union( Report.objects.filter(project = p) )
        ##return reports
#FIXME:        reports = Report.objects.none()
#FIXME:        for p in self.projects:
#FIXME:            if len( reports ) == 0:
#FIXME:                reports = Report.objects.filter(project = p)
#FIXME:            else:
#FIXME:                reports = reports.union( Report.objects.filter(project = p) )
#FIXME:        return reports
        return []

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
    def volumes(self):
        from volume.models import VolumeContainerBinding
        return [ binding.volume for binding in VolumeContainerBinding.objects.filter(container = self) ]

    def start(self):
        return start_environment(self)

    def stop(self):
        self.restart_reasons = None
        self.save()
        return stop_environment(self)

    def restart(self):
        self.restart_reasons = None
        self.save()
        return restart_environment(self)

    def check_state(self, retrieve_log = False):
        state = check_environment(self)
        if retrieve_log:
            state['podlog'] = fetch_containerlog(self)
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

