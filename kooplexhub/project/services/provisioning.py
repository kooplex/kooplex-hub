import os
import shutil
import logging
from dataclasses import dataclass

from django.utils import timezone

from hub.lib import grantaccess_group
from hub.lib.filesystem import (
    _mkdir,
    archive_directory,
)
from hub.models import Group
from hub.services.groups import (
    add_user_to_group,
    ensure_group,
)

from project.filesystem import (
    project_workdir,
)
from project.models import Project


logger = logging.getLogger(__name__)

MAX_PROVISIONING_ERROR_LENGTH = 4000


class ProjectProvisioningError(RuntimeError):
    pass


def _format_provisioning_error(error):
    return (
        f"{error.__class__.__name__}: {error}"
    )[:MAX_PROVISIONING_ERROR_LENGTH]


@dataclass(frozen=True, slots=True)
class ProjectFilesystemStatus:
    workdir: bool

    @property
    def ready(self):
        return self.workdir

    @property
    def missing(self):
        return () if self.workdir else ("workdir",)


def inspect_project_filesystem(
    *,
    project,
):
    return ProjectFilesystemStatus(
        workdir=os.path.isdir(
            project_workdir(project)
        ),
    )


def project_group_name(project):
    return f"p-{project.subpath}"


def provision_project_infrastructure(
    *,
    project,
    owner,
):
    group = ensure_group(
        name=project_group_name(project),
        grouptype=Group.TP_PROJECT,
    )

    Project.objects.filter(
        pk=project.pk,
    ).update(
        group=group,
    )

    project.group = group

    add_user_to_group(
        user=owner,
        group=group,
    )

    workdir = project_workdir(project)

    _mkdir(workdir)

    grantaccess_group(
        group,
        workdir,
        readonly=False,
        recursive=True,
    )

    status = inspect_project_filesystem(
        project=project,
    )

    if not status.ready:
        raise ProjectProvisioningError(
            "Project filesystem is incomplete: "
            + ", ".join(status.missing)
        )

    return group


def mark_project_provisioning_complete(
    *,
    project_id,
):
    return (
        Project.objects
        .filter(
            pk=project_id,
            provisioning_state=(
                Project.ProvisioningState.PREPARING
            ),
        )
        .update(
            provisioning_state=(
                Project.ProvisioningState.READY
            ),
            last_operation_error="",
            last_operation_failed_at=None,
            provisioned_at=timezone.now(),
        )
        == 1
    )


def mark_project_provisioning_failed(
    *,
    project_id,
    error,
):
    return (
        Project.objects
        .filter(
            pk=project_id,
            provisioning_state=(
                Project.ProvisioningState.PREPARING
            ),
        )
        .update(
            provisioning_state=(
                Project.ProvisioningState.FAILED
            ),
            last_operation_error=(
                _format_provisioning_error(
                    error
                )
            ),
            last_operation_failed_at=(
                timezone.now()
            ),
        )
        == 1
    )



def remove_project_workdir(
    project,
    *,
    archive,
):
    source = project_workdir(project)

    if not os.path.exists(source):
        return None

    if not os.path.isdir(source):
        raise RuntimeError(
            f"Project workdir is not a "
            f"directory: {source}"
        )

    if archive and os.listdir(source):
        return archive_directory(
            source,
            project_archive(project),
            remove=True,
        )

    shutil.rmtree(source)
    return None


