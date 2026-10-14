from dataclasses import dataclass, field

from django.conf import settings

from hub.confutils import merge_dataclass
from .models import Volume

@dataclass(frozen=True)
class VolumePresentationSettings:
    scope_icons: dict = field(default_factory=lambda: {
        Volume.Scope.PRIVATE: "bi-lock",
        Volume.Scope.INTERNAL: "bi-people",
        Volume.Scope.PUBLIC: "bi-globe",
        Volume.Scope.ATTACHMENT: "bi-paperclip",
    })
    provisioning_state_icons: dict = field(default_factory=lambda: {
        Volume.ProvisioningState.READY: "bi-check-circle text-success",
        Volume.ProvisioningState.PREPARING: "bi-hourglass-split text-warning",
        Volume.ProvisioningState.DELETING: "bi-trash text-secondary",
        Volume.ProvisioningState.FAILED: "bi-exclamation-circle text-danger",
    })
    unknown_state_icon: str = "bi-question-circle"


@dataclass(frozen=True)
class VolumeSettings:
    presentation: VolumePresentationSettings = field(default_factory=VolumePresentationSettings)
    admin_mounts_read_write: bool = True

    mountpoint: str = "/volume/{volume.folder}"

    attachment_claim: str = "attachments"
    # PVC-relative root; the Hub mount is rooted at this subpath.
    attachment_claim_subpath: str = ""
    attachment_subpath: str = "{folder}.{user.username}"
    attachment_hub_root: str = "/mnt/attachments"


VOLUME_SETTINGS = merge_dataclass(
    VolumeSettings(),
    getattr(settings, "VOLUME", {}),
)

