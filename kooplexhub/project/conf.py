from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from django.conf import settings

from hub.confutils import merge_dataclass
from hub.conf_types import (
    ArchivableMountSettings,
)
from .models import (
    Project, 
    UserProjectBinding,
)


@dataclass(frozen=True)
class MembershipEditorSettings:
    search_limit: int = 12
    minimum_query_length: int = 2


@dataclass(frozen=True)
class ProjectPresentationSettings:
    scope_icons: dict = field(
        default_factory=lambda: {
            Project.Scope.PUBLIC: "bi-globe",
            Project.Scope.INTERNAL: "bi-people",
            Project.Scope.PRIVATE: "bi-lock",
        }
    )

    member_role_icons: dict = field(
        default_factory=lambda: {
            UserProjectBinding.Role.CREATOR: (
                "bi-person-badge"
            ),
            UserProjectBinding.Role.ADMIN: (
                "bi-shield-lock"
            ),
            UserProjectBinding.Role.COLLABORATOR: (
                "bi-person"
            ),
        }
    )


def _default_project_mount():
    return ArchivableMountSettings(
        claim="big-storage",
        subpath="project/projects",
        folder="{project.subpath}",
        mountpoint="/project/{project.subpath}",
        mountpoint_hub="/mnt/projects",
        archive_name="project-{project.subpath}.{time}.tar.gz",
    )

@dataclass(frozen=True)
class ProjectMountsSettings:
    project: ArchivableMountSettings = field(
        default_factory=_default_project_mount
    )


@dataclass(frozen=True)
class ProjectSettings:
    membership_editor: MembershipEditorSettings = field(
        default_factory=MembershipEditorSettings
    )
    presentation: ProjectPresentationSettings = field(
        default_factory=ProjectPresentationSettings
    )
    mounts: ProjectMountsSettings = field(
        default_factory=ProjectMountsSettings
    )
    skip_workflow_chooser_when_no_joinable_project: bool = True


PROJECT_SETTINGS = merge_dataclass(
    ProjectSettings(),
    getattr(settings, "PROJECT", {}),
)
