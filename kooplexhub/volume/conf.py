from dataclasses import dataclass


@dataclass(frozen=True)
class VolumeAccessSettings:
    admin_mounts_read_write: bool = True
    mountpoint: str = "/volume/{volume.folder}"


VOLUME_SETTINGS = VolumeAccessSettings()

