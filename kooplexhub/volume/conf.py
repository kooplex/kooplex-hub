from dataclasses import dataclass

from django.conf import settings

from hub.confutils import merge_dataclass

@dataclass(frozen=True)
class VolumeSettings:
    admin_mounts_read_write: bool = True

    mountpoint: str = "/volume/{volume.folder}"

    attachment_claim: str = "attachments"
    attachment_subpath: str = "{folder}.{user.username}"
    attachment_hub_root: str = "/mnt/attachments"


VOLUME_SETTINGS = merge_dataclass(
    VolumeSettings(),
    getattr(settings, "VOLUME", {}),
)

