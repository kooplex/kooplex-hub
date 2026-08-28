import os
import time

from .conf import PROJECT_SETTINGS
from hub.conf import HUB_SETTINGS
from report.conf import REPORT_SETTINGS

def project_workdir(project):
    config = PROJECT_SETTINGS.mounts.project

    return os.path.join(
        config.mountpoint_hub,
        config.folder.format(
            project=project,
        ),
    )


def project_container_mountpoint(project):
    """
    Path at which the project is visible
    inside a user environment.
    """
    return (
        PROJECT_SETTINGS
        .mounts
        .project
        .mountpoint
        .format(project=project)
    )


def project_archive(project):
    config = PROJECT_SETTINGS.mounts.project

    return os.path.join(
        HUB_SETTINGS.mounts.garbage.mountpoint_hub,
        config.archive_name.format(
            project=project,
            time=time.time(),
        ),
    )

