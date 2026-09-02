from dataclasses import dataclass
import math


class ResourceConfigurationError(Exception):
    pass


@dataclass(frozen=True)
class ResolvedContainerResources:
    cpu_request_m: int
    cpu_limit_m: int
    memory_request_mib: int
    memory_limit_mib: int
    gpu: int


def _resolve_request(
    value,
    *,
    default,
    minimum,
    maximum,
    name,
):
    if value is None:
        value = default
        return max(minimum, min(value, maximum))

    if not minimum <= value <= maximum:
        raise ResourceConfigurationError(
            f"{name} request {value} is outside "
            f"configured range [{minimum}, {maximum}]"
        )

    return value


def _resolve_limit(
    explicit_limit,
    *,
    request,
    scale,
    maximum,
    name,
):
    if explicit_limit is None:
        return min(
            math.ceil(scale * request),
            maximum,
        )

    if explicit_limit < request:
        raise ResourceConfigurationError(
            f"{name} limit {explicit_limit} is below request {request}"
        )

    if explicit_limit > maximum:
        raise ResourceConfigurationError(
            f"{name} limit {explicit_limit} exceeds maximum {maximum}"
        )

    return explicit_limit



def resolve_container_resources(
    container,
    settings,
) -> ResolvedContainerResources:

    cpu_request_m = _resolve_request(
        container.requested_cpu_m,
        default=settings.default_cpu_m,
        minimum=settings.min_cpu_m,
        maximum=settings.max_cpu_m,
        name="cpu",
    )

    cpu_limit_m = _resolve_limit(
        container.limit_cpu_m,
        request=cpu_request_m,
        scale=settings.limit_scale_cpu,
        maximum=settings.max_cpu_m,
        name="cpu",
    )

    memory_request_mib = _resolve_request(
        container.requested_memory_mib,
        default=settings.default_memory_mib,
        minimum=settings.min_memory_mib,
        maximum=settings.max_memory_mib,
        name="memory",
    )

    memory_limit_mib = _resolve_limit(
        container.limit_memory_mib,
        request=memory_request_mib,
        scale=settings.limit_scale_memory,
        maximum=settings.max_memory_mib,
        name="memory",
    )

    gpu = (
        container.requested_gpu
        if container.requested_gpu is not None
        else settings.default_gpu
    )

    return ResolvedContainerResources(
        cpu_request_m=cpu_request_m,
        cpu_limit_m=cpu_limit_m,
        memory_request_mib=memory_request_mib,
        memory_limit_mib=memory_limit_mib,
        gpu=gpu,
    )


