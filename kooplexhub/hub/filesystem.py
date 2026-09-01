import os
import time

from .conf import HUB_SETTINGS


def user_home(user):
    config = HUB_SETTINGS.mounts.home

    return os.path.join(
        config.mountpoint_hub,
        config.folder.format(user=user),
    )


def user_garbage(user):
    config = HUB_SETTINGS.mounts.garbage

    if config is None:
        return None

    return os.path.join(
        config.mountpoint_hub,
        config.folder.format(user=user),
    )


def user_scratch(user):
    config = HUB_SETTINGS.mounts.scratch

    if config is None:
        return None

    return os.path.join(
        config.mountpoint_hub,
        config.folder.format(user=user),
    )


def user_home_archive(user):
    garbage = HUB_SETTINGS.mounts.garbage

    if garbage is None:
        return None

    home = HUB_SETTINGS.mounts.home

    return os.path.join(
        garbage.mountpoint_hub,
        home.archive_name.format(
            user=user,
            time=time.time(),
        ),
    )

