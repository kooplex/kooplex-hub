import os
import time

from .conf import PROJECT_SETTINGS
from hub.conf import HUB_SETTINGS

def _project_mount_path(
    config,
    project,
):
    return os.path.join(
        config.mountpoint_hub,
        config.folder.format(
            project=project,
        ),
    )


def project_workdir(project):
    return _project_mount_path(
        PROJECT_SETTINGS.mounts.project,
        project,
    )


def project_report_prepare_dir(project):
    return _project_mount_path(
        PROJECT_SETTINGS.mounts.report_prepare,
        project,
    )


def project_container_mountpoint(project):
    return (
        PROJECT_SETTINGS
        .mounts
        .project
        .mountpoint
        .format(project=project)
    )


def project_report_prepare_container_mountpoint(
    project,
):
    return (
        PROJECT_SETTINGS
        .mounts
        .report_prepare
        .mountpoint
        .format(project=project)
    )


def project_archive_path(project):
    config = PROJECT_SETTINGS.mounts.project

    return os.path.join(
        HUB_SETTINGS.mounts.garbage.mountpoint_hub,
        config.archive_name.format(
            project=project,
            time=time.time(),
        ),
    )


def project_report_prepare_archive_path(
    project,
):
    config = (
        PROJECT_SETTINGS
        .mounts
        .report_prepare
    )

    return os.path.join(
        HUB_SETTINGS.mounts.garbage.mountpoint_hub,
        config.archive_name.format(
            project=project,
            time=time.time(),
        ),
    )
