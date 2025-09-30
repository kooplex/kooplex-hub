import os
import time


from .conf import VOLUME_SETTINGS


def folder_attachment(volume):
    assert volume.scope == volume.Scope.ATTACHMENT, "Only attachments are automatically created"
    return os.path.join(
        VOLUME_SETTINGS['mounts']['attachment']['mountpoint_hub'],
        volume.subPath,
    )

