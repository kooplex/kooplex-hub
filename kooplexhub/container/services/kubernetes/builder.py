from __future__ import annotations

import logging
import os
from copy import deepcopy
from typing import Any, Iterable

from kubernetes import client as kubernetes_client

from container.models import Image
from education.conf import EDUCATION_SETTINGS
from hub.conf import HUB_SETTINGS
from kooplexhub.settings import KOOPLEX, REDIS_TELEPORT
from project.conf import PROJECT_SETTINGS
from report.conf import REPORT_SETTINGS
from volume.conf import VOLUME_SETTINGS

from .labels import dns_label, workload_labels, workload_name
from .resources import ResourcePolicy, build_resources
from .types import BuiltWorkload
from .volumes import VolumeBundle

logger = logging.getLogger(__name__)


def _iter(value: Any) -> list[Any]:
    if value is None:
        return []
    all_method = getattr(value, "all", None)
    if callable(all_method):
        value = all_method()
    return list(value)


def _get_setting(obj: Any, name: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _sanitize(value: Any) -> Any:
    """Convert Kubernetes model objects returned by old domain helpers to dicts."""
    return kubernetes_client.ApiClient().sanitize_for_serialization(value)


def resource_policy_from_settings(kubernetes_settings: Any) -> ResourcePolicy:
    """Build an explicit policy from either new or legacy setting names.

    Canonical units are millicores and MiB. Legacy aliases are accepted so the
    refactor can be wired before settings are renamed, but their values must be
    audited in the Kooplex configuration.
    """

    settings = _get_setting(kubernetes_settings, "resources", {})

    def first(*names: str, default: Any = None) -> Any:
        for name in names:
            value = _get_setting(settings, name, None)
            if value is not None:
                return value
        return default

    return ResourcePolicy(
        min_cpu_m=int(first("min_cpu_m", "min_cpu", default=0)),
        min_memory_mib=int(first("min_memory_mib", "min_memory", default=0)),
        max_cpu_m=_optional_int(first("max_cpu_m", default=None)),
        max_memory_mib=_optional_int(first("max_memory_mib", default=None)),
        max_gpu=_optional_int(first("max_gpu", default=None)),
        cpu_limit_m=_optional_int(
            first("cpu_limit_m", "limit_cpu_m", "limit_cpu", default=None)
        ),
        memory_limit_mib=_optional_int(
            first(
                "memory_limit_mib",
                "limit_memory_mib",
                "limit_memory",
                default=None,
            )
        ),
    )


def _optional_int(value: Any) -> int | None:
    return None if value is None else int(value)


class ContainerWorkloadBuilder:
    """Translate a Kooplex Container model into a Deployment workload spec.

    This class intentionally contains the project-specific model/settings logic.
    It performs no Kubernetes API calls, making its output straightforward to
    inspect in a Django shell and snapshot-test.
    """

    def __init__(
        self,
        kubernetes_settings: Any,
        *,
        resource_policy: ResourcePolicy | None = None,
    ):
        self.settings = kubernetes_settings
        self.namespace = _get_setting(kubernetes_settings, "namespace")
        self.resource_policy = resource_policy or resource_policy_from_settings(
            kubernetes_settings
        )

    def build(self, container: Any) -> BuiltWorkload:
        labels = workload_labels(container)
        pod_ports, service_ports = self._build_ports(container)
        volumes = VolumeBundle()
        env = self._build_environment_and_domain_mounts(container, volumes)
        self._build_user_volumes(container, volumes)

        pod_containers: list[dict[str, Any]] = []
        sidecar = self._build_davfs_sidecar(container, volumes)
        if sidecar is not None:
            pod_containers.append(sidecar)

        self._build_main_secret(container, volumes)
        pod_containers.append(
            self._build_main_container(container, pod_ports, volumes.mounts, env)
        )

        pod_spec: dict[str, Any] = {
            "containers": pod_containers,
            "volumes": volumes.volumes,
        }
        scheduling = deepcopy(getattr(container, "nodeSelector", {}) or {})
        if not isinstance(scheduling, dict):
            raise TypeError("container.nodeSelector must be a dictionary")
        pod_spec.update(scheduling)

        return BuiltWorkload(
            name=workload_name(container),
            namespace=self.namespace,
            labels=labels,
            pod_labels=labels,
            pod_spec=pod_spec,
            service_ports=service_ports,
        )

    def _build_ports(
        self, container: Any
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        pod_ports: list[dict[str, Any]] = []
        service_ports: list[dict[str, Any]] = []
        for proxy in _iter(getattr(container, "proxies", [])):
            port = int(proxy.svc_port)
            name = dns_label(str(proxy.name), max_length=15)
            pod_ports.append({"containerPort": port, "name": name})
            service_ports.append(
                {
                    "port": port,
                    "targetPort": port,
                    "protocol": "TCP",
                    "name": name,
                }
            )
        return pod_ports, service_ports

    def _build_environment_and_domain_mounts(
        self, container: Any, volumes: VolumeBundle
    ) -> list[dict[str, Any]]:
        image_type = container.image.imagetype
        interactive_types = {Image.ImageType.PROJECT, Image.ImageType.JOB}
        published_types = {
            Image.ImageType.REPORT,
            Image.ImageType.API,
            Image.ImageType.APP,
        }

        if image_type in interactive_types:
            env = self._format_environment(KOOPLEX["environmental_variables"], container)
            self._add_identity_mounts(container, volumes, env)
            self._add_home_scratch_course_project_mounts(container, volumes)
        elif image_type in published_types:
            env = self._format_environment(
                KOOPLEX["environmental_variables_report"], container
            )
            env.append(
                {
                    "name": "REPORT_FOLDER",
                    "value": REPORT_SETTINGS["mounts"]["report"]["mountpoint"],
                }
            )
            if image_type == Image.ImageType.REPORT:
                binding = container.reportbindings.get(container=container)
                report_cfg = REPORT_SETTINGS["mounts"]["report"]
                volumes.add_pvc(
                    claim_name=report_cfg["claim"],
                    mount_path=report_cfg["mountpoint"].format(
                        user=container.user, report=binding.report
                    ),
                    sub_path=report_cfg["folder"].format(
                        user=container.user, report=binding.report
                    ),
                )
        else:
            raise ValueError(f"Unknown image type {image_type}")

        env.extend(_sanitize(_iter(getattr(container, "env_variables", []))))
        return env

    @staticmethod
    def _format_environment(mapping: dict[str, Any], container: Any) -> list[dict[str, str]]:
        return [
            {"name": str(name), "value": str(value).format(container=container)}
            for name, value in mapping.items()
        ]

    def _add_identity_mounts(
        self,
        container: Any,
        volumes: VolumeBundle,
        env: list[dict[str, Any]],
    ) -> None:
        volumes.add_config_map(
            config_map_name="nslcd",
            mount_path=_get_setting(_get_setting(self.settings, "nslcd"), "mount_path"),
            default_mode=0o400,
            items=[{"key": "nslcd", "path": "nslcd.conf"}],
        )

        init_items = [
            {"key": "nsswitch", "path": "01-nsswitch"},
            {"key": "nslcd", "path": "02-nslcd"},
            {"key": "usermod", "path": "03-usermod"},
        ]
        if container.user.profile.can_teleport and container.start_teleport:
            init_items.append({"key": "teleport", "path": "06-teleport"})
            env.append({"name": "REDIS_TELEPORT", "value": REDIS_TELEPORT})

        volumes.add_config_map(
            config_map_name="initscripts",
            mount_path=_get_setting(
                _get_setting(self.settings, "initscripts"), "mount_path"
            ),
            default_mode=0o777,
            items=init_items,
        )
        jobs = _get_setting(self.settings, "jobs")
        volumes.add_config_map(
            config_map_name="job.py",
            mount_path=_get_setting(jobs, "jobpy"),
            default_mode=0o777,
            items=[{"key": "job", "path": "job"}],
        )

    def _add_home_scratch_course_project_mounts(
        self, container: Any, volumes: VolumeBundle
    ) -> None:
        if container.image.require_home:
            self._add_configured_pvc(
                volumes, HUB_SETTINGS["mounts"]["home"], user=container.user
            )
            self._add_configured_pvc(
                volumes, HUB_SETTINGS["mounts"]["garbage"], user=container.user
            )

        scratch = HUB_SETTINGS["mounts"].get("scratch")
        if container.user.profile.has_scratch and scratch:
            self._add_configured_pvc(volumes, scratch, user=container.user)

        for course in _iter(getattr(container, "courses", [])):
            self._add_configured_pvc(
                volumes,
                EDUCATION_SETTINGS["mounts"]["workdir"],
                user=container.user,
                course=course,
            )
            self._add_configured_pvc(
                volumes,
                EDUCATION_SETTINGS["mounts"]["public"],
                user=container.user,
                course=course,
            )

        for project in _iter(getattr(container, "projects", [])):
            self._add_configured_pvc(
                volumes,
                PROJECT_SETTINGS["mounts"]["project"],
                user=container.user,
                project=project,
            )
            self._add_configured_pvc(
                volumes,
                REPORT_SETTINGS["mounts"]["prepare"],
                user=container.user,
                project=project,
            )

    @staticmethod
    def _add_configured_pvc(
        volumes: VolumeBundle, config: dict[str, Any], **format_values: Any
    ) -> None:
        sub_path = os.path.join(
            config.get("subpath", ""), config["folder"].format(**format_values)
        )
        volumes.add_pvc(
            claim_name=config["claim"],
            mount_path=config["mountpoint"].format(**format_values),
            sub_path=sub_path,
        )

    def _build_user_volumes(self, container: Any, volumes: VolumeBundle) -> None:
        for volume in _iter(getattr(container, "volumes", [])):
            key = (
                "attachment"
                if volume.scope == volume.Scope.ATTACHMENT
                else "volume"
            )
            mount_cfg = VOLUME_SETTINGS["mounts"][key]
            volumes.add_pvc(
                claim_name=volume.claim,
                mount_path=mount_cfg["mountpoint"].format(volume=volume),
                sub_path=volume.subpath,
            )

    def _build_main_secret(self, container: Any, volumes: VolumeBundle) -> None:
        jobs = _get_setting(self.settings, "jobs")
        secrets = _get_setting(self.settings, "secrets")
        token_name = _get_setting(jobs, "token_name")
        volumes.add_secret(
            secret_name=container.user.username,
            mount_path=_get_setting(secrets, "mount_dir"),
            items=[{"key": token_name, "path": token_name}],
            default_mode=0o444,
            identity=_get_setting(secrets, "name", "main-secrets"),
        )

    def _build_davfs_sidecar(
        self, container: Any, volumes: VolumeBundle
    ) -> dict[str, Any] | None:
        if not getattr(container, "start_seafile", False):
            return None

        from service.models.service import SeafileService

        service = SeafileService.objects.first()
        if service is None:
            raise RuntimeError("start_seafile is enabled but no SeafileService exists")
        service.sync_pw(container.user)

        secret_name = volumes.add_secret(
            secret_name=container.user.username,
            mount_path=service.secret_mount_dir,
            items=[
                {
                    "key": service.kubernetes_secret_name,
                    "path": service.secret_file,
                }
            ],
            default_mode=0o444,
            identity="davfs-secrets",
        )
        # The secret mount belongs to the sidecar, not the main container.
        sidecar_secret_mount = volumes.mounts.pop()

        shared_name = volumes.add_empty_dir(
            identity="davfs-seafile",
            mount_path=service.mount_dir,
            size_limit="30Gi",
            mount_propagation="HostToContainer",
        )
        main_shared_mount = volumes.mounts[-1]
        sidecar_shared_mount = {
            "name": shared_name,
            "mountPath": service.mount_dir,
            "mountPropagation": "Bidirectional",
        }

        return {
            "name": "davfs-sidecar",
            "image": _get_setting(
                self.settings,
                "davfs_sidecar_image",
                "image-registry.vo.elte.hu/sidecar-davfs2",
            ),
            "volumeMounts": [sidecar_secret_mount, sidecar_shared_mount],
            "imagePullPolicy": _get_setting(self.settings, "image_pull_policy"),
            "env": _sanitize(service.get_envs(container.user)),
            "securityContext": {
                "privileged": True,
                "capabilities": {"add": ["SYS_ADMIN"]},
            },
        }

    def _build_main_container(
        self,
        container: Any,
        pod_ports: list[dict[str, Any]],
        volume_mounts: list[dict[str, Any]],
        env: list[dict[str, Any]],
    ) -> dict[str, Any]:
        result: dict[str, Any] = {
            "name": workload_name(container),
            "image": container.image.name,
            "volumeMounts": volume_mounts,
            "ports": pod_ports,
            "imagePullPolicy": _get_setting(self.settings, "image_pull_policy"),
            "env": env,
            "resources": build_resources(container, self.resource_policy),
        }
        if container.image.command:
            result["command"] = ["/bin/bash", "-c", container.image.command]

        if container.image.liveness_probe:
            probe = container.image.liveness_probe.as_api_object()
            probe = _sanitize(probe)
            http_get = probe.get("httpGet") or probe.get("http_get")
            if http_get and http_get.get("path"):
                http_get["path"] = http_get["path"].format(container=container)
            result["livenessProbe"] = probe
        return result
