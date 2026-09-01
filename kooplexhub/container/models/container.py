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
        default=CONTAINER_SETTINGS.kubernetes.resources.default_cpu_m,
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
        default=CONTAINER_SETTINGS.kubernetes.resources.default_memory_mib,
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

    def __str__(self):
        return self.label

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
        return bool(self.restart_reasons)



