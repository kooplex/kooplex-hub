from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class ResourceVector:
    cpu_m: int = 0
    memory_bytes: int = 0
    gpu: int = 0

    def __add__(self, other: "ResourceVector") -> "ResourceVector":
        return ResourceVector(
            cpu_m=self.cpu_m + other.cpu_m,
            memory_bytes=self.memory_bytes + other.memory_bytes,
            gpu=self.gpu + other.gpu,
        )

    def __sub__(self, other: "ResourceVector") -> "ResourceVector":
        return ResourceVector(
            cpu_m=self.cpu_m - other.cpu_m,
            memory_bytes=self.memory_bytes - other.memory_bytes,
            gpu=self.gpu - other.gpu,
        )

    @classmethod
    def sum(cls, values: list["ResourceVector"]) -> "ResourceVector":
        total = cls()
        for value in values:
            total += value
        return total


@dataclass(frozen=True)
class RouteSpec:
    base_path: str
    endpoint: str


@dataclass(frozen=True)
class BuiltWorkload:
    name: str
    namespace: str
    labels: dict[str, str]
    pod_labels: dict[str, str]
    pod_spec: dict[str, Any]
    service_ports: list[dict[str, Any]]


@dataclass
class PodResourceSnapshot:
    name: str
    namespace: str
    node: str | None
    phase: str | None
    container_id: str | None
    requested: ResourceVector
    usage: ResourceVector | None = None


@dataclass
class NodeResourceSnapshot:
    name: str
    allocatable: ResourceVector
    requested: ResourceVector
    available: ResourceVector
    usage: ResourceVector | None = None


@dataclass
class ClusterResourceSnapshot:
    inventory_source: str
    usage_source: str
    allocatable: ResourceVector
    requested: ResourceVector
    available: ResourceVector
    nodes: list[NodeResourceSnapshot] = field(default_factory=list)
    pods: list[PodResourceSnapshot] = field(default_factory=list)
    observed_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    warning: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
