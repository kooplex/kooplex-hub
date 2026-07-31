from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from django.conf import settings


@dataclass(frozen=True)
class MembershipEditorSettings:
    search_limit: int = 12
    minimum_query_length: int = 2


@dataclass(frozen=True)
class ProjectSettings:
    membership_editor: MembershipEditorSettings = field(
        default_factory=MembershipEditorSettings
    )



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
