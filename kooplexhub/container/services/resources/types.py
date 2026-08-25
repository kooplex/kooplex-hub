from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class ResourceRequest:
    cpu_m: int
    memory_mib: int
    gpu: int = 0


@dataclass(frozen=True)
class NodeResourceState:
    name: str

    allocatable_cpu_m: int
    allocatable_memory_mib: int
    allocatable_gpu: int

    requested_cpu_m: int = 0
    requested_memory_mib: int = 0
    requested_gpu: int = 0

    live_cpu_m: int | None = None
    live_memory_mib: int | None = None

    unschedulable: bool = False
    labels: dict[str, str] = field(default_factory=dict)
    taints: list[str] = field(default_factory=list)

    @property
    def free_cpu_m(self) -> int:
        return max(0, self.allocatable_cpu_m - self.requested_cpu_m)

    @property
    def free_memory_mib(self) -> int:
        return max(0, self.allocatable_memory_mib - self.requested_memory_mib)

    @property
    def free_gpu(self) -> int:
        return max(0, self.allocatable_gpu - self.requested_gpu)


@dataclass(frozen=True)
class ClusterResourceSnapshot:
    nodes: list[NodeResourceState]
    created_at: datetime
    source: str
    confidence: str
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class FitResult:
    fits_now: bool
    possible_somewhere: bool
    status: str
    reason: str

    cpu_green_limit_m: int
    memory_green_limit_mib: int
    gpu_green_limit: int
