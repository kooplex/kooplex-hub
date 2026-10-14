from pathlib import Path
import shutil

from ..conf import VOLUME_SETTINGS


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
    return path


def delete_attachment_storage(volume) -> None:
    path = attachment_host_path(volume)

    if path.exists():
        shutil.rmtree(path)


