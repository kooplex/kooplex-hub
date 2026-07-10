from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from django.conf import settings


@dataclass(frozen=True)
class KubernetesResourcesSettings:
    default_cpu: float = 0.2
    default_gpu: int = 0
    default_memory: float = 1
    default_idletime: int = 28

    min_cpu: float = 0.2
    min_gpu: int = 0
    min_memory: float = 0.5
    min_idletime: int = 1

    max_cpu: float = 4
    max_gpu: int = 0
    max_memory: float = 2
    max_idletime: int = 24

    limit_cpu: float = 5
    limit_gpu: int = 0
    limit_memory: float = 28


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
class ContainerWssSettings:
    live: str = "wss://localhost/hub/ws/container/live/"
    fetchlog: str = "wss://localhost/hub/ws/container/fetchlog/{user.id}/"
    monitor_node: str = "wss://localhost/hub/ws/monitor/node/{user.id}/"


@dataclass(frozen=True)
class ContainerSettings:
    kubernetes: KubernetesSettings = field(default_factory=KubernetesSettings)
    proxy: ProxySettings = field(default_factory=ProxySettings)
    wss: ContainerWssSettings = field(default_factory=ContainerWssSettings)


def _merge_dataclass(default_obj, override: dict | None):
    """
    Recursive dataclass override helper.

    Example:
        default = KubernetesSettings()
        override = {"namespace": "kooplex", "resources": {"max_cpu": 8}}

    Result:
        KubernetesSettings(namespace="kooplex",
                           resources=KubernetesResourcesSettings(max_cpu=8, ...))
    """

    if not override:
        return default_obj

    values = {}

    for field_info in default_obj.__dataclass_fields__.values():
        name = field_info.name
        default_value = getattr(default_obj, name)

        if name not in override:
            values[name] = default_value
            continue

        override_value = override[name]

        if hasattr(default_value, "__dataclass_fields__"):
            values[name] = _merge_dataclass(
                default_value,
                override_value,
            )
        else:
            values[name] = override_value

    unknown_keys = set(override) - set(default_obj.__dataclass_fields__)

    if unknown_keys:
        raise ValueError(
            f"Unknown container setting keys for {type(default_obj).__name__}: "
            f"{', '.join(sorted(unknown_keys))}"
        )

    return type(default_obj)(**values)


CONTAINER_SETTINGS = _merge_dataclass(
    ContainerSettings(),
    getattr(settings, "CONTAINER", {}),
)
