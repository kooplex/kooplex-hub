from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import (
    MinLengthValidator,
)
from django.core.exceptions import ValidationError

from .image import Image


User = get_user_model()


class Container(models.Model):
    class State(models.TextChoices):
        NOTPRESENT = 'np', 'Not present.'
        STARTING = 'starting', 'Starting...'
        RUNNING = 'run', 'Running fine.'
        NEED_RESTART = 'restart', 'Restart required'
        ERROR = 'oops', 'Error occured'
        STOPPING = 'stopping', 'Stopping...'

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(requested_cpu_m__isnull=True)
                    | models.Q(limit_cpu_m__isnull=True)
                    | models.Q(limit_cpu_m__gte=models.F("requested_cpu_m"))
                ),
                name="container_cpu_limit_gte_request",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(requested_memory_mib__isnull=True)
                    | models.Q(limit_memory_mib__isnull=True)
                    | models.Q(limit_memory_mib__gte=models.F("requested_memory_mib"))
                ),
                name="container_memory_limit_gte_request",
            ),
        ]

    name = models.CharField(
        max_length=200, 
        null=False, 
        validators=[ 
            MinLengthValidator(3, message="Name must be at least 3 characters."), 
        ],
    )
    label = models.CharField(max_length = 200, null = False, unique = True)
    user = models.ForeignKey(User, on_delete = models.CASCADE, null = False)
    image = models.ForeignKey(Image, on_delete = models.CASCADE, null = False)

    requested_cpu_m = models.PositiveIntegerField(
        null=True,
        blank=True,
        default=None,
    )

    limit_cpu_m = models.PositiveIntegerField(
        null=True,
        blank=True,
        default=None,
    )

    cpu_usage_m = models.PositiveIntegerField(
        null=True,
        blank=True,
        default=None,
    )

    requested_gpu = models.PositiveIntegerField(
        null=True,
        blank=True,
        default=None,
    )

    requested_memory_mib = models.PositiveIntegerField(
        null=True,
        blank=True,
        default=None,
    )

    limit_memory_mib = models.PositiveIntegerField(
        null=True,
        blank=True,
        default=None,
    )

    memory_usage_mib = models.PositiveIntegerField(
        null=True,
        blank=True,
        default=None,
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

    requested_uptime_hours = models.IntegerField(
        null=True, 
        blank=True, 
        default=None,
    )
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


    def clean(self):
        super().clean()

        errors = {}

        if (
            self.requested_cpu_m is not None
            and self.limit_cpu_m is not None
            and self.requested_cpu_m > self.limit_cpu_m
        ):
            errors["limit_cpu_m"] = (
                "CPU limit must be greater than or equal to CPU request."
            )

        if (
            self.requested_memory_mib is not None
            and self.limit_memory_mib is not None
            and self.requested_memory_mib > self.limit_memory_mib
        ):
            errors["limit_memory_mib"] = (
                "Memory limit must be greater than or equal to memory request."
            )

        if errors:
            raise ValidationError(errors)


