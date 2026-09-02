from kubernetes import client

from ..compute_resolver import (
    ResolvedContainerResources,
)


def build_resources(
    resolved: ResolvedContainerResources,
) -> client.V1ResourceRequirements:
    requests = {
        "cpu": f"{resolved.cpu_request_m}m",
        "memory": f"{resolved.memory_request_mib}Mi",
    }

    limits = {
        "cpu": f"{resolved.cpu_limit_m}m",
        "memory": f"{resolved.memory_limit_mib}Mi",
    }

    if resolved.gpu > 0:
        gpu = str(resolved.gpu)
        requests["nvidia.com/gpu"] = gpu
        limits["nvidia.com/gpu"] = gpu

    return client.V1ResourceRequirements(
        requests=requests,
        limits=limits,
    )

