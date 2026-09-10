from dataclasses import dataclass


@dataclass(frozen=True)
class VolumeSettings:
    admin_mounts_read_write: bool = True

    mountpoint: str = "/volume/{volume.folder}"

    attachment_claim: str = "attachments"
    attachment_subpath: str = "{volume.folder}.{user.username}"
    attachment_hub_root: str = "/mnt/attachments"


VOLUME_SETTINGS = VolumeSettings()

