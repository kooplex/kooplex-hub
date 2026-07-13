from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any


def _volume_name(kind: str, identity: str) -> str:
    digest = hashlib.sha1(f"{kind}:{identity}".encode("utf-8")).hexdigest()[:12]
    return f"kooplex-{kind}-{digest}"


@dataclass
class VolumeBundle:
    """Collect volumes and mounts with deterministic names for idempotent patches."""

    volumes: list[Any] = field(default_factory=list)
    mounts: list[Any] = field(default_factory=list)
    _names: dict[tuple[str, str], str] = field(default_factory=dict)

    def add_pvc(
        self,
        *,
        claim_name: str,
        mount_path: str,
        sub_path: str | None = None,
        read_only: bool = False,
        mount_propagation: str | None = None,
    ) -> str:
        key = ("pvc", claim_name)
        name = self._names.get(key)
        if name is None:
            name = _volume_name(*key)
            self._names[key] = name
            self.volumes.append(
                {"name": name, "persistentVolumeClaim": {"claimName": claim_name}}
            )
        self.add_mount(
            name=name,
            mount_path=mount_path,
            sub_path=sub_path,
            read_only=read_only,
            mount_propagation=mount_propagation,
        )
        return name

    def add_config_map(
        self,
        *,
        config_map_name: str,
        mount_path: str,
        items: list[dict[str, Any]] | None = None,
        default_mode: int | None = None,
        read_only: bool = True,
    ) -> str:
        key = ("cm", config_map_name)
        name = self._names.get(key)
        if name is None:
            name = _volume_name(*key)
            self._names[key] = name
            source: dict[str, Any] = {"name": config_map_name}
            if items is not None:
                source["items"] = items
            if default_mode is not None:
                source["defaultMode"] = default_mode
            self.volumes.append({"name": name, "configMap": source})
        self.add_mount(name=name, mount_path=mount_path, read_only=read_only)
        return name

    def add_secret(
        self,
        *,
        secret_name: str,
        mount_path: str,
        items: list[dict[str, Any]] | None = None,
        default_mode: int | None = None,
        read_only: bool = True,
        identity: str | None = None,
    ) -> str:
        key = ("secret", identity or secret_name)
        name = self._names.get(key)
        if name is None:
            name = _volume_name(*key)
            self._names[key] = name
            source: dict[str, Any] = {"secretName": secret_name}
            if items is not None:
                source["items"] = items
            if default_mode is not None:
                source["defaultMode"] = default_mode
            self.volumes.append({"name": name, "secret": source})
        self.add_mount(name=name, mount_path=mount_path, read_only=read_only)
        return name

    def add_empty_dir(
        self,
        *,
        identity: str,
        mount_path: str,
        medium: str | None = None,
        size_limit: str | None = None,
        mount_propagation: str | None = None,
    ) -> str:
        key = ("emptydir", identity)
        name = self._names.get(key)
        if name is None:
            name = _volume_name(*key)
            self._names[key] = name
            source: dict[str, Any] = {}
            if medium:
                source["medium"] = medium
            if size_limit:
                source["sizeLimit"] = size_limit
            self.volumes.append({"name": name, "emptyDir": source})
        self.add_mount(
            name=name,
            mount_path=mount_path,
            mount_propagation=mount_propagation,
        )
        return name

    def add_mount(
        self,
        *,
        name: str,
        mount_path: str,
        sub_path: str | None = None,
        read_only: bool = False,
        mount_propagation: str | None = None,
    ) -> None:
        mount: dict[str, Any] = {"name": name, "mountPath": mount_path}
        if sub_path:
            mount["subPath"] = sub_path
        if read_only:
            mount["readOnly"] = True
        if mount_propagation:
            mount["mountPropagation"] = mount_propagation
        self.mounts.append(mount)
