from .compute import (
    ContainerComputeDisplayView,
    ContainerComputeEditView,
    ContainerComputeUpdateView,
)
from .name import (
    ContainerNameDisplayView,
    ContainerNameEditView,
    ContainerNameUpdateView,
    ContainerCreateNameValidateView,
)
from .open_service import ContainerOpenButtonPartialView
from .runtime import (
    ContainerFetchlogButtonPartialView,
    ContainerRestartButtonPartialView,
    ContainerStartButtonPartialView,
    ContainerStopButtonPartialView,
    ContainerBackendStatusPartialView,
)
from .uptime import (
    ContainerUptimeDisplayView,
    ContainerUptimeEditView,
    ContainerUptimeUpdateView,
)

__all__ = [
    "ContainerStartButtonPartialView",
    "ContainerStopButtonPartialView",
    "ContainerRestartButtonPartialView",
    "ContainerFetchlogButtonPartialView",
    "ContainerBackendStatusPartialView",
    "ContainerNameDisplayView",
    "ContainerNameEditView",
    "ContainerNameUpdateView",
    "ContainerCreateNameValidateView",
    "ContainerUptimeDisplayView",
    "ContainerUptimeEditView",
    "ContainerUptimeUpdateView",
    "ContainerComputeDisplayView",
    "ContainerComputeEditView",
    "ContainerComputeUpdateView",
    "ContainerOpenButtonPartialView",
]
