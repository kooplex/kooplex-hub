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
from ..lib import start_environment, stop_environment, restart_environment, check_environment

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
    #TODO:
    # on the long run:
    #       let friendly name take over the name as a model attribute, 
    #            the name needs to be unique
    #       generate and store the label pre_save
    #       no need to have suffix, and friendly_name any longer
    # needs a careful migration! 
    # thus
    # for now in the form the name will be hidden and generated pre_save
    #                     and the friendly name attribute will carry the name label

    name = models.CharField(max_length = 200, null = False, validators = [my_alphanumeric_validator('Enter a valid container name containing only letters and numbers.')])
    friendly_name = models.CharField(max_length = 200, null = False)
    user = models.ForeignKey(User, on_delete = models.CASCADE, null = False)
    suffix = models.CharField(max_length = 200, null = True, default = None, blank = True)
    image = models.ForeignKey(Image, on_delete = models.CASCADE, null = False)
    launched_at = models.DateTimeField(null = True, blank = True)

    state = models.CharField(max_length = 16, choices = ST_LOOKUP.items(), default = ST_NOTPRESENT)
    restart_reasons = models.CharField(max_length = 512, null = True, blank = True)
    last_message = models.CharField(max_length = 512, null = True)
    last_message_at = models.DateTimeField(default = None, null = True, blank = True)
    log = models.TextField(max_length = 10512, null = True)
    node = models.TextField(max_length = 64, null = True, blank = True)

    class Meta:
        unique_together = [['user', 'name', 'suffix']]

    def __lt__(self, c):
        return self.launched_at < c.launched_at

    def __str__(self):
        return self.label


    @property
    def label(self):
        return f"{self.user.username}-{self.name}-{self.suffix}".lower() if self.suffix else f"{self.user.username}-{self.name}".lower()

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
    def url_public(self):
        return self.default_proxy.url_public(self)

    def wait_until_ready(self):
        from kooplexhub.lib import keeptrying
        for _ in range(5):
            resp = keeptrying(method = requests.get, times = 5, url = self.url_public, timeout = .05, allow_redirects = False)
            logger.info('Get %s -> [%d]' % (self.url_public, resp.status_code))
            time.sleep(.1)
            if resp.status_code != 503:
                return resp
            logger.warning('Proxy target missing: %s' % self.url_public)

    @property
    def env_variables(self):
        for envmap in EnvVarMapping.objects.filter(image = self.image):
            yield { "name": envmap.name, "value": envmap.valuemap.format(container = self) }

    @property
    def uptime(self):
        timenow = now()
        delta = timenow - self.launched_at
        return delta if self.is_running else -1

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
    def attachments(self):
        from .attachment import AttachmentContainerBinding
        return [ binding.attachment for binding in AttachmentContainerBinding.objects.filter(container = self) ]

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

    def check_state(self):
        return check_environment(self)

    def mark_restart(self, reason):
        if self.state not in [ self.ST_RUNNING, self.ST_NEED_RESTART ]:
            return False
        if self.restart_reasons:
            self.restart_reasons += ', ' + reason
        else:
            self.restart_reasons = reason
        self.state = self.ST_NEED_RESTART
        self.save()
        return True

