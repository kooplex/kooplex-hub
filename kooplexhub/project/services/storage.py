import os
import shutil

from hub.lib import grantaccess_group
from hub.lib.filesystem import (
    _mkdir,
    archive_directory,
)

from project.filesystem import (
    project_archive_path,
    project_report_prepare_archive_path,
    project_report_prepare_dir,
    project_workdir,
)


def ensure_project_storage(
    *,
    project,
    group,
):
    for path in (
        project_workdir(project),
        project_report_prepare_dir(project),
    ):
        _mkdir(path)

        grantaccess_group(
            group,
            path,
            readonly=False,
            recursive=True,
        )


def _remove_directory(
    source,
    *,
    archive,
    archive_path,
):
    if not os.path.exists(source):
        return None

    if not os.path.isdir(source):
        raise RuntimeError(
            f"Expected directory: {source}"
        )

    if archive and os.listdir(source):
        return archive_directory(
            source,
            archive_path,
            remove=True,
        )

    shutil.rmtree(source)
    return None


def remove_project_storage(
    *,
    project,
    archive,
):
    project_result = _remove_directory(
        project_workdir(project),
        archive=archive,
        archive_path=(
            project_archive_path(project)
        ),
    )

    prepare_result = _remove_directory(
        project_report_prepare_dir(project),
        archive=archive,
        archive_path=(
            project_report_prepare_archive_path(
                project
            )
        ),
    )

    return project_result, prepare_result


