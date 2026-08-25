from collections import defaultdict
from dataclasses import dataclass


@dataclass
class ResourceSum:
    cpu_m: int = 0
    memory_mib: int = 0
    gpu: int = 0


def get_kooplex_requested_resources_by_node() -> dict[str, ResourceSum]:
    """
    Temporary fallback until we get cluster-wide pod-list permissions.

    Fill this from your Django models / pod status stream.

    Expected result:
      {
        "node-1": ResourceSum(cpu_m=2000, memory_mib=8192, gpu=1),
        "node-2": ResourceSum(cpu_m=1000, memory_mib=4096, gpu=0),
      }
    """

    by_node: dict[str, ResourceSum] = defaultdict(ResourceSum)

    from container.models import Container
    
    running = Container.objects.filter(
        state__in=[Container.State.STARTING, Container.State.RUNNING, Container.State.NEED_RESTART],
    ).exclude(
        node__isnull=True,
    )
    
    for c in running:
        node = c.node
        by_node[node].cpu_m += c.requested_cpu_m
        by_node[node].memory_mib += c.requested_memory_mib
        by_node[node].gpu += c.requested_gpu or 0

    return dict(by_node)
