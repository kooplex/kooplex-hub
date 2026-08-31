import os
import shutil
import logging
from dataclasses import dataclass

from django.utils import timezone

from hub.models import Group
from hub.services.groups import (
    add_user_to_group,
    ensure_group,
)

from ..filesystem import (
    project_workdir,
    project_report_prepare_dir,
)
from ..models import Project
from .storage import (
    ensure_project_storage,
)


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
    report_prepare: bool

    @property
    def ready(self):
        return (
            self.workdir
            and self.report_prepare
        )

    @property
    def missing(self):
        missing = []

        if not self.workdir:
            missing.append("workdir")

        if not self.report_prepare:
            missing.append("report_prepare")

        return tuple(missing)



def inspect_project_filesystem(
    *,
    project,
):
    return ProjectFilesystemStatus(
        workdir=os.path.isdir(
            project_workdir(project)
        ),
        report_prepare=os.path.isdir(
            project_report_prepare_dir(
                project
            )
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

    ensure_project_storage(
        project=project,
        group=group,
    )

    status = inspect_project_filesystem(
        project=project,
    )

    if not status.ready:
        raise ProjectProvisioningError(
            "Project filesystem incomplete: "
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
            state=Project.State.PREPARING,
        )
        .update(
            state=Project.State.READY,
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
            state=Project.State.PREPARING,
        )
        .update(
            state=Project.State.FAILED,
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



