import logging

from django.db import models
from django.urls import reverse
from django.core.validators import (
    MinLengthValidator,
    MinValueValidator,
)

from .image import Image
from .envvar import EnvVarMapping
from django.contrib.auth import get_user_model

from container.services.mounts import get_container_mount_items

User = get_user_model()

from ..conf import CONTAINER_SETTINGS
from project.models import ProjectContainerBinding

logger = logging.getLogger(__name__)

class Container(models.Model):
    class State(models.TextChoices):
        NOTPRESENT = 'np', 'Not present.'
        STARTING = 'starting', 'Starting...'
        RUNNING = 'run', 'Running fine.'
        NEED_RESTART = 'restart', 'Restart required'
        ERROR = 'oops', 'Error occured'
        STOPPING = 'stopping', 'Stopping...'

    name = models.CharField(
        max_length = 200, 
        null = False, 
        validators=[ 
            MinLengthValidator(3, message="Name must be at least 3 characters."), 
        ],
    )
    label = models.CharField(max_length = 200, null = False, unique = True)
    user = models.ForeignKey(User, on_delete = models.CASCADE, null = False)
    image = models.ForeignKey(Image, on_delete = models.CASCADE, null = False)

    requested_cpu_m = models.DecimalField(
        null=True,
        blank=True,
        decimal_places=1,
        max_digits=7,
        default=CONTAINER_SETTINGS.kubernetes.resources.default_cpu,
        validators=[MinValueValidator(0)],
    )
    
    cpu_usage_m = models.PositiveIntegerField(
        null=True,
        blank=True,
        default=None,
    )
    
    requested_gpu = models.PositiveIntegerField(
        null=True,
        blank=True,
        default=CONTAINER_SETTINGS.kubernetes.resources.default_gpu,
    )
    
    requested_memory_mib = models.DecimalField(
        null=True,
        blank=True,
        decimal_places=1,
        max_digits=8,
        default=CONTAINER_SETTINGS.kubernetes.resources.default_memory,
        validators=[MinValueValidator(0)],
    )
    
    memory_usage_mib = models.DecimalField(
        null=True,
        blank=True,
        decimal_places=1,
        max_digits=10,
        default=None,
        validators=[MinValueValidator(0)],
    )
    
    resource_usage_at = models.DateTimeField(
        null=True,
        blank=True,
        default=None,
    )


    launched_at = models.DateTimeField(null = True, blank = True)
    start_teleport = models.BooleanField(default = False)
    start_ssh = models.BooleanField(default = False)#FIXME: is it really used somewhere????
    start_seafile = models.BooleanField(default = False)

    require_running = models.BooleanField(default = False)
    state = models.CharField(max_length = 16, choices = State.choices, default = State.NOTPRESENT)
    state_backend = models.CharField(max_length = 32, null = True, blank = True, default = None)
    state_lastcheck_at = models.DateTimeField(default = None, null = True, blank = True)

    restart_reasons = models.CharField(max_length = 500, null = True, blank = True)

    requested_node = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        help_text="Requested Kubernetes node or placement preference. Configuration field.",
    )
    
    runtime_node = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        help_text="Observed Kubernetes node where the pod is currently running. Updated by watcher.",
    )

    requested_uptime_hours = models.IntegerField( null = True, blank = True, default=CONTAINER_SETTINGS.kubernetes.resources.default_idletime)
    idle = models.IntegerField( null = True, blank = True, default=None)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "name"],
                name="unique_container_name_per_user",
            ),
        ]
        indexes = [
            models.Index(fields=["user", "state"]),
            models.Index(fields=["user", "require_running"]),
            models.Index(fields=["state", "require_running"]),
            models.Index(fields=["label"]),
        ]
        ordering = ["image", "name"]

    def __lt__(self, c):
        return self.launched_at < c.launched_at

    def __str__(self):
        return self.label

    @property
    def image_modal_url(self):
        if not self.pk:
            return None

        return reverse(
            "container:image_modal",
            args=[self.pk],
        )

    @property
    def mounts_modal_url(self):
        if not self.pk:
            return None

        return reverse(
            "container:mounts_modal",
            args=[self.pk],
        )

    @property
    def mount_summary(self):
        mounts = get_container_mount_items(self)

        projects = mounts["projects"]
        courses = mounts["courses"]
        volumes = mounts["volumes"]

        return {
            "project_count": len(projects),
            "course_count": len(courses),
            "volume_count": len(volumes),
            "projects": projects,
            "courses": courses,
            "volumes": volumes,
            "tooltip": self._mount_summary_tooltip(
                projects=projects,
                courses=courses,
                volumes=volumes,
            ),
        }

    def _mount_summary_tooltip(self, projects, courses, volumes):
        lines = []

        if projects:
            lines.append("Projects: " + ", ".join(project.name for project in projects))

        if courses:
            lines.append("Courses: " + ", ".join(course.name for course in courses))

        if volumes:
            lines.append("Storage: " + ", ".join(volume.folder for volume in volumes))

        return "\n".join(lines) or "No custom mounts."


    #TODO: put these in a mixin
    @property
    def name_dom_id(self):
        return f"container-{self.pk}-name"

    @property
    def name_edit_url(self):
        return reverse("container:name_edit", args=[self.pk])

    @property
    def name_display_url(self):
        return reverse("container:name_display", args=[self.pk])

    @property
    def name_update_url(self):
        return reverse("container:name_update", args=[self.pk])


    @property
    def uptime_dom_id(self):
        return f"container-{self.pk}-uptime"
    
    @property
    def uptime_display_url(self):
        return reverse("container:uptime_display", args=[self.pk])
    
    @property
    def uptime_edit_url(self):
        return reverse("container:uptime_edit", args=[self.pk])
    
    @property
    def uptime_update_url(self):
        return reverse("container:uptime_update", args=[self.pk])



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
        selector={'kubernetes.io/hostname': self.requested_node} if self.requested_node else dict(CONTAINER_SETTINGS.kubernetes.node_selector)
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


    def clear_runtime_measurements(self) -> None:
        """Clear ephemeral measurements when no running Pod is being measured."""
        self.cpu_usage_m = None
        self.memory_usage_mib = None
        self.resource_usage_at = None
        self.idle = None


    def start(self):
        from container.tasks import start_container
    
        self.require_running = True
        self.restart_reasons = []
        self.save(update_fields=["require_running", "restart_reasons"])
        return start_container(self.user_id, self.pk)
    
    
    def stop(self):
        from container.tasks import stop_container
    
        self.require_running = False
        self.restart_reasons = []
        self.clear_runtime_measurements()
        self.save(
            update_fields=[
                "require_running",
                "restart_reasons",
                "cpu_usage_m",
                "memory_usage_mib",
                "resource_usage_at",
                "idle",
            ]
        )
        return stop_container(self.user_id, self.pk)
    
    
    def restart(self):
        from container.tasks import restart_container
    
        self.require_running = True
        self.restart_reasons = []
        self.clear_runtime_measurements()
        self.save(
            update_fields=[
                "require_running",
                "restart_reasons",
                "cpu_usage_m",
                "memory_usage_mib",
                "resource_usage_at",
                "idle",
            ]
        )
        return restart_container(self.user_id, self.pk)
    
    
    def retrieve_log(self):
        from container.services.kubernetes.wiring import build_pod_operations
    
        return build_pod_operations().logs_for_container(self)


    @property
    def is_running(self):
        return self.state in [
            self.State.RUNNING,
            self.State.NEED_RESTART,
        ]

    @property
    def is_transitioning(self):
        return self.state in [
            self.State.STARTING,
            self.State.STOPPING,
        ]

    @property
    def needs_restart(self):
        return self.state == self.State.NEED_RESTART

    def mark_restart(self, reason, save=True):
        if self.state not in [
            self.State.RUNNING,
            self.State.NEED_RESTART,
        ]:
            return False

        if self.restart_reasons:
            self.restart_reasons += "; " + reason
        else:
            self.restart_reasons = reason

        self.state = self.State.NEED_RESTART

        if save:
            self.save(
                update_fields=[
                    "restart_reasons",
                    "state",
                ]
            )

        return True


