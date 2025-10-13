import logging

from django.db import models
from django.urls import reverse
from django.core.validators import MinLengthValidator

from .image import Image
from .envvar import EnvVarMapping
from django.contrib.auth import get_user_model

User = get_user_model()

from ..conf import CONTAINER_SETTINGS

logger = logging.getLogger(__name__)

class Container(models.Model):
    class State(models.TextChoices):
        NOTPRESENT = 'np', 'Not present.'
        STARTING = 'starting', 'Starting...'
        RUNNING = 'run', 'Running fine.'
        NEED_RESTART = 'restart', 'Restart required'
        ERROR = 'oops', 'Error occured'
        STOPPING = 'stopping', 'Stopping...'

    name = models.CharField(max_length = 200, null = False, validators=[ MinLengthValidator(3, message="Name must be at least 3 characters.") ])
    label = models.CharField(max_length = 200, null = False, unique = True)
    user = models.ForeignKey(User, on_delete = models.CASCADE, null = False)
    image = models.ForeignKey(Image, on_delete = models.CASCADE, null = False)
    launched_at = models.DateTimeField(null = True, blank = True)
    start_teleport = models.BooleanField(default = False)
    start_ssh = models.BooleanField(default = False)#FIXME: is it really used somewhere????
    start_seafile = models.BooleanField(default = False)

    require_running = models.BooleanField(default = False)
    state = models.CharField(max_length = 16, choices = State.choices, default = State.NOTPRESENT)
    state_backend = models.CharField(max_length = 32, null = True, blank = True, default = None)
    state_lastcheck_at = models.DateTimeField(default = None, null = True, blank = True)

    restart_reasons = models.CharField(max_length = 500, null = True, blank = True)

    node = models.TextField(max_length = 64, null = True, blank = True)
    nodemanifest = models.TextField(max_length = 64, null = True, blank = True)
    cpurequest = models.DecimalField(null = True, blank = True, decimal_places=1, max_digits=4, default=CONTAINER_SETTINGS["kubernetes"]["resources"]["default_cpu"])
    cpuusage = models.DecimalField(null = True, blank = True, decimal_places=1, max_digits=4, default=None)
    gpurequest = models.IntegerField(null = True, blank = True, default=CONTAINER_SETTINGS["kubernetes"]["resources"]["default_gpu"])
    memoryrequest = models.DecimalField( null = True, blank = True, decimal_places=1, max_digits=5, default=CONTAINER_SETTINGS["kubernetes"]["resources"]["default_memory"])
    memoryusage = models.DecimalField(null = True, blank = True, decimal_places=1, max_digits=5, default=None)
    idletime = models.IntegerField( null = True, blank = True, default=CONTAINER_SETTINGS["kubernetes"]["resources"]["default_idletime"])
    idle = models.IntegerField( null = True, blank = True, default=None)

    class Meta:
        unique_together = [['user', 'name']]

    def __lt__(self, c):
        return self.launched_at < c.launched_at

    def __str__(self):
        return self.label

    @property
    def link_drop(self):
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
        return { b.proxy for b in self.image.proxybindings.all() }


    def addroutes(self):
        for proxy in self.proxies:
            proxy.addroute(self)


    def removeroutes(self):
        for proxy in self.proxies:
            proxy.removeroute(self)

    @property
    def views(self):
        v = []
        for p in self.proxies:
            v.extend(p.views.filter(openable=True))
        return v


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


    @property
    def projects(self):
        return { b.project for b in self.projectbindings.all() } if self.pk else {}

    @property
    def courses(self):
        return { b.course for b in self.coursebindings.all() } if self.pk else {}

    @property
    def volumes(self):
        return { b.volume for b in self.volumebindings.all() } if self.pk else {}

    @property
    def nodeSelector(self):
        selector={'kubernetes.io/hostname': self.node} if self.node else dict(CONTAINER_SETTINGS['kubernetes']['nodeSelector_k8s'])
        return {"nodeSelector": selector} if selector else {}


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

    def start(self):
        from ..tasks import start_container
        self.require_running=True
        start_container(self.user.id, self.id)

    def stop(self):
        from ..tasks import stop_container
        self.require_running=False
        self.restart_reasons=None
        self.cpuusage=None
        self.memoryusage=None
        self.idle=None
        self.save()
        self.removeroutes()
        stop_container(self.user.id, self.id)

    def restart(self):
        from ..tasks import stop_container
        self.require_running=True
        self.restart_reasons=None
        self.cpuusage=None
        self.memoryusage=None
        self.idle=None
        self.save()
        stop_container(self.user.id, self.id)

    def retrieve_log(self):
        from ..lib import fetch_containerlog
        return  fetch_containerlog(self)

    @property
    def is_running(self):
        return self.state in [ self.State.RUNNING, self.State.NEED_RESTART ]

    def mark_restart(self, reason, save = True):
        if self.state not in [ self.State.RUNNING, self.State.NEED_RESTART ]:
            return False
        if self.restart_reasons:
            self.restart_reasons += '; ' + reason
        else:
            self.restart_reasons = reason
        self.state = self.State.NEED_RESTART
        if save:
            self.save()
        return True

