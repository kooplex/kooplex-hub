from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .quantities import cpu_quantity, memory_quantity


@dataclass(frozen=True)
class ResourcePolicy:
    """All CPU values are millicores; all memory values are MiB."""

    min_cpu_m: int = 0
    min_memory_mib: int = 0
    max_cpu_m: int | None = None
    max_memory_mib: int | None = None
    max_gpu: int | None = None
    cpu_limit_m: int | None = None
    memory_limit_mib: int | None = None


def _bounded(value: int, minimum: int, maximum: int | None, name: str) -> int:
    result = max(int(value), int(minimum))
    if maximum is not None and result > maximum:
        raise ValueError(f"Requested {name}={result} exceeds configured maximum {maximum}")
    return result


def build_resources(container: Any, policy: ResourcePolicy) -> dict[str, dict[str, str]]:
    cpu_m = _bounded(container.requested_cpu_m, policy.min_cpu_m, policy.max_cpu_m, "CPU")
    memory_mib = _bounded(
        container.requested_memory_mib,
        policy.min_memory_mib,
        policy.max_memory_mib,
        "memory",
    )
    gpu = _bounded(container.requested_gpu, 0, policy.max_gpu, "GPU")

    cpu_limit_m = max(cpu_m, policy.cpu_limit_m or cpu_m)
    memory_limit_mib = max(memory_mib, policy.memory_limit_mib or memory_mib)

    requests = {
        "cpu": cpu_quantity(cpu_m),
        "memory": memory_quantity(memory_mib),
    }
    limits = {
        "cpu": cpu_quantity(cpu_limit_m),
        "memory": memory_quantity(memory_limit_mib),
    }
    if gpu:
        # Extended GPU resources use the same integer request and limit.
        requests["nvidia.com/gpu"] = str(gpu)
        limits["nvidia.com/gpu"] = str(gpu)

    return {"requests": requests, "limits": limits}
