from __future__ import annotations

from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class MountSettings:
    claim: str
    subpath: str
    folder: str
    mountpoint: str
    mountpoint_hub: str


@dataclass(frozen=True, slots=True)
class ArchivableMountSettings(MountSettings):
    archive_name: str


@dataclass(frozen=True, slots=True)
class TreeMountSettings(MountSettings):
    folder_top: str


@dataclass(frozen=True, slots=True)
class ArchivableTreeMountSettings(TreeMountSettings):
    archive_name: str

