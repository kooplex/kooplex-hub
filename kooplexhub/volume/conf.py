from dataclasses import dataclass


@dataclass(frozen=True)
class VolumeAccessSettings:
    admin_mounts_read_write: bool = True


VOLUME_SETTINGS = VolumeAccessSettings()

