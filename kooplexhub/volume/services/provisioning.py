from pathlib import Path
import shutil

from ..conf import VOLUME_SETTINGS
from ..models import UserVolumeBinding
from hub.lib.filesystem import _grantaccess, user_has_folder_access


def validate_relative_subpath(value: str, *, allow_empty: bool = False) -> str:
    """Validate a PVC-relative path without silently normalizing traversal."""
    value = str(value)
    if value == "" and allow_empty:
        return ""
    parts = value.split("/")
    if (not value or value.startswith("/") or
            any(part in ("", ".", "..") for part in parts)):
        raise ValueError(f"Invalid PVC-relative subpath: {value!r}")
    return value


def attachment_host_path(volume) -> Path:
    if volume.scope != volume.Scope.ATTACHMENT:
        raise ValueError("Filesystem lifecycle only applies to attachments.")

    root = validate_relative_subpath(
        VOLUME_SETTINGS.attachment_claim_subpath, allow_empty=True
    )
    full = validate_relative_subpath(volume.subpath)
    if root:
        prefix = root + "/"
        if not full.startswith(prefix):
            raise ValueError(
                f"Attachment subpath {full!r} is outside configured "
                f"PVC root {root!r}; refusing filesystem operation."
            )
        relative = full[len(prefix):]
    else:
        relative = full

    hub_root = Path(VOLUME_SETTINGS.attachment_hub_root)
    if not hub_root.is_absolute():
        raise ValueError("attachment_hub_root must be absolute")
    return hub_root / relative


def ensure_attachment_storage(volume) -> Path:
    path = attachment_host_path(volume)
    path.mkdir(
        parents=True,
        exist_ok=True,
    )
    owner_binding = (
        UserVolumeBinding.objects
        .select_related("user__profile")
        .get(volume=volume, role=UserVolumeBinding.Role.OWNER)
    )
    owner = owner_binding.user
    # This path is already rooted at the Hub's PVC subPath.
    # Fail provisioning (and keep the volume non-READY) if ACLs fail.
    # Effective permissions on the directory and any existing children.
    _grantaccess(
        owner, str(path), readonly=False, recursive=True, follow=False
    )

    # NFSv4 inherit-only ACE on the attachment root: new files/directories
    # written by the Hub (or another privileged process) inherit owner
    # permissions. Do not recursively set fdi on regular files.
    from hub.lib.filesystem import acl_backend
    if acl_backend == "nfs4":
        _grantaccess(
            owner, str(path), readonly=False, recursive=False, follow=True
        )
    if not user_has_folder_access(owner, str(path), writable=True):
        raise RuntimeError(f"Attachment owner ACL verification failed: {path}")
    return path


def delete_attachment_storage(volume) -> None:
    path = attachment_host_path(volume)

    if path.exists():
        shutil.rmtree(path)


