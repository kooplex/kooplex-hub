from pathlib import Path
import shutil

from ..conf import VOLUME_SETTINGS


def attachment_host_path(volume) -> Path:
    if volume.scope != volume.Scope.ATTACHMENT:
        raise ValueError(
            "Filesystem lifecycle only applies to attachments."
        )

    return (
        Path(VOLUME_SETTINGS.attachment_hub_root)
        / volume.subpath
    )


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


