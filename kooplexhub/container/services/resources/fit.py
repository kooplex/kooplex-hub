from dataclasses import dataclass
from .types import ClusterResourceSnapshot, FitResult, ResourceRequest

@dataclass(frozen=True)
class ResourceShortage:
    dimension: str
    requested: int
    best_capacity: int
    best_free: int
    unit: str
    label: str


def clamp(value: int, low: int, high: int) -> int:
    return max(low, min(value, high))


def node_can_fit(node, request: ResourceRequest) -> bool:
    if node.unschedulable:
        return False

    return (
        request.cpu_m <= node.free_cpu_m
        and request.memory_mib <= node.free_memory_mib
        and request.gpu <= node.free_gpu
    )


def node_possible_by_capacity(node, request: ResourceRequest) -> bool:
    if node.unschedulable:
        return False

    return (
        request.cpu_m <= node.allocatable_cpu_m
        and request.memory_mib <= node.allocatable_memory_mib
        and request.gpu <= node.allocatable_gpu
    )


def max_green_for_dimension(
    snapshot: ClusterResourceSnapshot,
    request: ResourceRequest,
    dimension: str,
) -> int:
    best = 0

    for node in snapshot.nodes:
        if node.unschedulable:
            continue

        if dimension != "cpu" and request.cpu_m > node.free_cpu_m:
            continue

        if dimension != "memory" and request.memory_mib > node.free_memory_mib:
            continue

        if dimension != "gpu" and request.gpu > node.free_gpu:
            continue

        if dimension == "cpu":
            best = max(best, node.free_cpu_m)
        elif dimension == "memory":
            best = max(best, node.free_memory_mib)
        elif dimension == "gpu":
            best = max(best, node.free_gpu)
        else:
            raise ValueError(f"Unknown dimension: {dimension}")

    return best


def _format_cpu(cpu_m: int) -> str:
    if cpu_m % 1000 == 0:
        return f"{cpu_m // 1000} CPU"
    return f"{cpu_m / 1000:g} CPU"


def _format_memory(memory_mib: int) -> str:
    if memory_mib >= 1024 and memory_mib % 1024 == 0:
        return f"{memory_mib // 1024} GiB RAM"
    if memory_mib >= 1024:
        return f"{memory_mib / 1024:g} GiB RAM"
    return f"{memory_mib} MiB RAM"


def _format_gpu(gpu: int) -> str:
    return f"{gpu} GPU" if gpu == 1 else f"{gpu} GPUs"


def _max_capacity(snapshot: ClusterResourceSnapshot, dimension: str) -> int:
    if dimension == "cpu":
        return max((n.allocatable_cpu_m for n in snapshot.nodes if not n.unschedulable), default=0)
    if dimension == "memory":
        return max((n.allocatable_memory_mib for n in snapshot.nodes if not n.unschedulable), default=0)
    if dimension == "gpu":
        return max((n.allocatable_gpu for n in snapshot.nodes if not n.unschedulable), default=0)
    raise ValueError(f"Unknown dimension: {dimension}")


def _max_free(snapshot: ClusterResourceSnapshot, dimension: str) -> int:
    if dimension == "cpu":
        return max((n.free_cpu_m for n in snapshot.nodes if not n.unschedulable), default=0)
    if dimension == "memory":
        return max((n.free_memory_mib for n in snapshot.nodes if not n.unschedulable), default=0)
    if dimension == "gpu":
        return max((n.free_gpu for n in snapshot.nodes if not n.unschedulable), default=0)
    raise ValueError(f"Unknown dimension: {dimension}")


def _find_absolute_shortages(
    snapshot: ClusterResourceSnapshot,
    request: ResourceRequest,
) -> list[ResourceShortage]:
    """
    Absolute shortage means no node has enough allocatable capacity,
    even if the cluster were empty.
    """

    checks = [
        (
            "cpu",
            request.cpu_m,
            _max_capacity(snapshot, "cpu"),
            _max_free(snapshot, "cpu"),
            "m",
            "CPU",
        ),
        (
            "memory",
            request.memory_mib,
            _max_capacity(snapshot, "memory"),
            _max_free(snapshot, "memory"),
            "MiB",
            "memory",
        ),
        (
            "gpu",
            request.gpu,
            _max_capacity(snapshot, "gpu"),
            _max_free(snapshot, "gpu"),
            "",
            "GPU",
        ),
    ]

    shortages = []

    for dimension, requested, best_capacity, best_free, unit, label in checks:
        if requested > best_capacity:
            shortages.append(
                ResourceShortage(
                    dimension=dimension,
                    requested=requested,
                    best_capacity=best_capacity,
                    best_free=best_free,
                    unit=unit,
                    label=label,
                )
            )

    return shortages


def _find_current_shortages(
    snapshot: ClusterResourceSnapshot,
    request: ResourceRequest,
) -> list[ResourceShortage]:
    """
    Current shortage means the request is possible on some node by capacity,
    but no node has enough free resources now.

    This is approximate because resources are cross-dependent.
    """

    checks = [
        (
            "cpu",
            request.cpu_m,
            _max_capacity(snapshot, "cpu"),
            _max_free(snapshot, "cpu"),
            "m",
            "CPU",
        ),
        (
            "memory",
            request.memory_mib,
            _max_capacity(snapshot, "memory"),
            _max_free(snapshot, "memory"),
            "MiB",
            "memory",
        ),
        (
            "gpu",
            request.gpu,
            _max_capacity(snapshot, "gpu"),
            _max_free(snapshot, "gpu"),
            "",
            "GPU",
        ),
    ]

    shortages = []

    for dimension, requested, best_capacity, best_free, unit, label in checks:
        if requested > best_free:
            shortages.append(
                ResourceShortage(
                    dimension=dimension,
                    requested=requested,
                    best_capacity=best_capacity,
                    best_free=best_free,
                    unit=unit,
                    label=label,
                )
            )

    return shortages


def _format_shortage(shortage: ResourceShortage, absolute: bool) -> str:
    if shortage.dimension == "cpu":
        requested = _format_cpu(shortage.requested)
        best_capacity = _format_cpu(shortage.best_capacity)
        best_free = _format_cpu(shortage.best_free)
    elif shortage.dimension == "memory":
        requested = _format_memory(shortage.requested)
        best_capacity = _format_memory(shortage.best_capacity)
        best_free = _format_memory(shortage.best_free)
    elif shortage.dimension == "gpu":
        requested = _format_gpu(shortage.requested)
        best_capacity = _format_gpu(shortage.best_capacity)
        best_free = _format_gpu(shortage.best_free)
    else:
        requested = str(shortage.requested)
        best_capacity = str(shortage.best_capacity)
        best_free = str(shortage.best_free)

    if absolute:
        return (
            f"Requested {requested}, but the largest known node capacity is "
            f"{best_capacity}."
        )

    return (
        f"Requested {requested}, but the largest currently free amount is "
        f"{best_free}."
    )


def explain_impossible_request(
    snapshot: ClusterResourceSnapshot,
    request: ResourceRequest,
) -> str:
    shortages = _find_absolute_shortages(snapshot, request)

    if shortages:
        # Prefer GPU explanation because it is often the most discrete/blocking resource.
        shortages = sorted(
            shortages,
            key=lambda s: {"gpu": 0, "memory": 1, "cpu": 2}.get(s.dimension, 99),
        )

        return _format_shortage(shortages[0], absolute=True)

    return "No known node can satisfy this resource combination."


def explain_current_shortage(
    snapshot: ClusterResourceSnapshot,
    request: ResourceRequest,
) -> str:
    shortages = _find_current_shortages(snapshot, request)

    if shortages:
        shortages = sorted(
            shortages,
            key=lambda s: {"gpu": 0, "memory": 1, "cpu": 2}.get(s.dimension, 99),
        )

        return _format_shortage(shortages[0], absolute=False)

    return "The request is valid, but no single node currently has the required free resource combination."


def evaluate_resource_request(
    snapshot: ClusterResourceSnapshot,
    request: ResourceRequest,
) -> FitResult:
    fits_now = any(node_can_fit(node, request) for node in snapshot.nodes)
    possible_somewhere = any(
        node_possible_by_capacity(node, request)
        for node in snapshot.nodes
    )

    if fits_now:
        status = "fits_now"
        reason = "Likely startable now based on the latest resource snapshot."
    elif possible_somewhere:
        status = "valid_but_wait"
        reason = explain_current_shortage(snapshot, request)
    else:
        status = "impossible"
        reason = explain_impossible_request(snapshot, request)

    return FitResult(
        fits_now=fits_now,
        possible_somewhere=possible_somewhere,
        status=status,
        reason=reason,
        cpu_green_limit_m=max_green_for_dimension(snapshot, request, "cpu"),
        memory_green_limit_mib=max_green_for_dimension(snapshot, request, "memory"),
        gpu_green_limit=max_green_for_dimension(snapshot, request, "gpu"),
    )
