from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from django.conf import settings

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


@dataclass(frozen=True)
class ProjectSettings:
    membership_editor: MembershipEditorSettings = field(
        default_factory=MembershipEditorSettings
    )
    presentation: ProjectPresentationSettings = field(
        default_factory=ProjectPresentationSettings
    )
    skip_workflow_chooser_when_no_joinable_project: bool = True



def _merge_dataclass(default_obj, override: dict | None):

    if not override:
        return default_obj

    values = {}

    for field_info in default_obj.__dataclass_fields__.values():
        name = field_info.name
        default_value = getattr(default_obj, name)

        if name not in override:
            values[name] = default_value
            continue

        override_value = override[name]

        if hasattr(default_value, "__dataclass_fields__"):
            values[name] = _merge_dataclass(
                default_value,
                override_value,
            )
        else:
            values[name] = override_value

    unknown_keys = set(override) - set(default_obj.__dataclass_fields__)

    if unknown_keys:
        raise ValueError(
            f"Unknown container setting keys for {type(default_obj).__name__}: "
            f"{', '.join(sorted(unknown_keys))}"
        )

    return type(default_obj)(**values)


PROJECT_SETTINGS = _merge_dataclass(
    ProjectSettings(),
    getattr(settings, "PROJECT", {}),
)
