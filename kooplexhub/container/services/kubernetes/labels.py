from __future__ import annotations

import hashlib
import re
from typing import Any, Mapping

_DNS_RE = re.compile(r"[^a-z0-9-]+")

APP_NAME_LABEL = "app.kubernetes.io/name"
INSTANCE_LABEL = "app.kubernetes.io/instance"
MANAGED_BY_LABEL = "app.kubernetes.io/managed-by"
CONTAINER_ID_LABEL = "kooplex.io/container-id"
USER_LABEL = "kooplex.io/user"

KOOPLEX_APP_NAME = "kooplex-container"
KOOPLEX_MANAGED_BY = "kooplex"


def dns_label(value: str, *, max_length: int = 63) -> str:
    normalized = _DNS_RE.sub("-", value.lower()).strip("-") or "kooplex"
    if len(normalized) <= max_length:
        return normalized
    digest = hashlib.sha1(value.encode("utf-8")).hexdigest()[:8]
    return f"{normalized[: max_length - 9].rstrip('-')}-{digest}"


def workload_name(container: Any) -> str:
    return dns_label(str(container.label))


def workload_labels(container: Any) -> dict[str, str]:
    name = workload_name(container)
    return {
        APP_NAME_LABEL: KOOPLEX_APP_NAME,
        INSTANCE_LABEL: name,
        MANAGED_BY_LABEL: KOOPLEX_MANAGED_BY,
        CONTAINER_ID_LABEL: str(container.pk),
        USER_LABEL: dns_label(str(container.user.username)),
    }


def managed_workload_labels() -> dict[str, str]:
    """Labels shared by every Deployment/Pod managed by Kooplex."""
    return {
        APP_NAME_LABEL: KOOPLEX_APP_NAME,
        MANAGED_BY_LABEL: KOOPLEX_MANAGED_BY,
    }


def selector(labels: Mapping[str, str]) -> str:
    return ",".join(f"{key}={value}" for key, value in sorted(labels.items()))


def managed_workload_selector() -> str:
    return selector(managed_workload_labels())


def object_labels(obj: Any) -> Mapping[str, str]:
    metadata = getattr(obj, "metadata", None)
    return getattr(metadata, "labels", None) or {}


def container_id_from_object(obj: Any) -> int | None:
    value = object_labels(obj).get(CONTAINER_ID_LABEL)
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def instance_name_from_object(obj: Any) -> str | None:
    return object_labels(obj).get(INSTANCE_LABEL)
