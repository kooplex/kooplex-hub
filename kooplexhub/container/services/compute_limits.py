from dataclasses import dataclass

from ..conf import CONTAINER_SETTINGS


@dataclass(frozen=True)
class ComputeLimits:
    cpu_min: float
    cpu_max: float
    cpu_step: float

    memory_min: float
    memory_max: float
    memory_step: float

    gpu_min: int
    gpu_max: int
    gpu_step: int = 1


class ComputeLimitsProvider:
    """
    Current implementation uses configured fallback limits.

    Later this can read a cluster-state cache without changing the
    views or templates.
    """

    def for_container(self, container) -> ComputeLimits:
        resources = CONTAINER_SETTINGS.kubernetes.resources

        return ComputeLimits(
            cpu_min=resources.min_cpu,
            cpu_max=resources.max_cpu,
            cpu_step=0.1,

            memory_min=resources.min_memory,
            memory_max=resources.max_memory,
            memory_step=0.5,

            gpu_min=resources.min_gpu,
            gpu_max=resources.max_gpu,
            gpu_step=1,
        )

#    def for_container(self, container):
#        cluster_state = cluster_resource_cache.current()
#        return cluster_state.limits_for(container)


compute_limits_provider = ComputeLimitsProvider()
