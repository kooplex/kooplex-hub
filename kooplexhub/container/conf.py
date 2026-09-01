from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from django.conf import settings

from hub.confutils import merge_dataclass


@dataclass(frozen=True)
class KubernetesResourcesSettings:
    # Canonical units:
    # CPU: millicores
    # memory: MiB
    default_cpu_m: int = 200
    default_gpu: int = 0
    default_memory_mib: float = 1
    default_idletime: int = 28

    min_cpu_m: int = 200
    min_gpu: int = 0
    min_memory_mib: float = 0.5
    min_idletime: int = 1

    max_cpu_m: int = 4000
    max_gpu: int = 0
    max_memory_mib: float = 2
    max_idletime: int = 24

    limit_cpu_m: float = 5000
    limit_gpu: int = 0
    limit_memory_mib: float = 28


@dataclass(frozen=True)
class KubernetesSecretsSettings:
    name: str = "main-secrets"
    mount_dir: str = "/.secrets"


@dataclass(frozen=True)
class KubernetesJobsSettings:
    namespace: str = "jobs"
    jobpy: str = "/etc/jobtool"
    token_name: str = "job_token"


@dataclass(frozen=True)
class KubernetesNslcdSettings:
    mount_path: str = "/etc/mnt"


@dataclass(frozen=True)
class KubernetesInitScriptsSettings:
    mount_path: str = "/.init_scripts"


@dataclass(frozen=True)
class KubernetesSettings:
    namespace: str = "default"
    node_selector: dict[str, Any] = field(default_factory=dict)
    image_pull_policy: str = "IfNotPresent"

    resources: KubernetesResourcesSettings = field(
        default_factory=KubernetesResourcesSettings
    )
    secrets: KubernetesSecretsSettings = field(
        default_factory=KubernetesSecretsSettings
    )
    jobs: KubernetesJobsSettings = field(
        default_factory=KubernetesJobsSettings
    )
    nslcd: KubernetesNslcdSettings = field(
        default_factory=KubernetesNslcdSettings
    )
    initscripts: KubernetesInitScriptsSettings = field(
        default_factory=KubernetesInitScriptsSettings
    )


@dataclass(frozen=True)
class ProxySettings:
    proto: str = "https"
    url: str = "http://localhost:8001/api"
    check_container: str = "routes/notebook/{container.label}"
    auth_token: str = ""


@dataclass(frozen=True)
class ComputeWidgetSettings:
    warning_ratio: float = 0.90
    critical_ratio: float = 1.00


@dataclass(frozen=True)
class ContainerSettings:
    kubernetes: KubernetesSettings = field(default_factory=KubernetesSettings)
    proxy: ProxySettings = field(default_factory=ProxySettings)
    compute_widget: ComputeWidgetSettings = field(default_factory=ComputeWidgetSettings)


CONTAINER_SETTINGS = merge_dataclass(
    ContainerSettings(),
    getattr(settings, "CONTAINER", {}),
)
