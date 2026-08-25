from datetime import datetime

from django.utils import timezone
from kubernetes import client
from kubernetes.client.exceptions import ApiException

from .k8s_client import get_kubernetes_api_client
from .quantities import parse_cpu_to_millicores, parse_memory_to_mib
from .types import NodeResourceState, ClusterResourceSnapshot
from .kooplex_state import get_kooplex_requested_resources_by_node


GPU_RESOURCE_KEYS = [
    "nvidia.com/gpu",
    "amd.com/gpu",
]


def _parse_gpu(allocatable: dict) -> int:
    for key in GPU_RESOURCE_KEYS:
        value = allocatable.get(key)
        if value:
            return int(value)
    return 0


def _taints_to_strings(taints) -> list[str]:
    if not taints:
        return []

    result = []

    for taint in taints:
        result.append(
            f"{taint.key}={taint.value}:{taint.effect}"
            if taint.value is not None
            else f"{taint.key}:{taint.effect}"
        )

    return result


def read_nodes() -> list[NodeResourceState]:
    api_client = get_kubernetes_api_client()
    v1 = client.CoreV1Api(api_client)

    nodes = v1.list_node(_request_timeout=10).items

    result = []

    for node in nodes:
        alloc = node.status.allocatable or {}

        result.append(
            NodeResourceState(
                name=node.metadata.name,
                allocatable_cpu_m=parse_cpu_to_millicores(alloc.get("cpu")),
                allocatable_memory_mib=parse_memory_to_mib(alloc.get("memory")),
                allocatable_gpu=_parse_gpu(alloc),
                unschedulable=bool(node.spec.unschedulable),
                labels=node.metadata.labels or {},
                taints=_taints_to_strings(node.spec.taints),
            )
        )

    return result


def read_node_metrics() -> dict[str, dict[str, int]]:
    api_client = get_kubernetes_api_client()
    metrics_api = client.CustomObjectsApi(api_client)

    metrics_by_node: dict[str, dict[str, int]] = {}

    try:
        node_metrics = metrics_api.list_cluster_custom_object(
            group="metrics.k8s.io",
            version="v1beta1",
            plural="nodes",
            _request_timeout=10,
        )
    except ApiException:
        return metrics_by_node

    for item in node_metrics.get("items", []):
        usage = item.get("usage", {})
        metrics_by_node[item["metadata"]["name"]] = {
            "live_cpu_m": parse_cpu_to_millicores(usage.get("cpu")),
            "live_memory_mib": parse_memory_to_mib(usage.get("memory")),
        }

    return metrics_by_node


def build_node_metrics_snapshot() -> ClusterResourceSnapshot:
    nodes = read_nodes()
    metrics_by_node = read_node_metrics()

    enriched_nodes = []

    for node in nodes:
        metrics = metrics_by_node.get(node.name, {})

        enriched_nodes.append(
            NodeResourceState(
                name=node.name,
                allocatable_cpu_m=node.allocatable_cpu_m,
                allocatable_memory_mib=node.allocatable_memory_mib,
                allocatable_gpu=node.allocatable_gpu,
                requested_cpu_m=node.requested_cpu_m,
                requested_memory_mib=node.requested_memory_mib,
                requested_gpu=node.requested_gpu,
                live_cpu_m=metrics.get("live_cpu_m"),
                live_memory_mib=metrics.get("live_memory_mib"),
                unschedulable=node.unschedulable,
                labels=node.labels,
                taints=node.taints,
            )
        )

    return ClusterResourceSnapshot(
        nodes=enriched_nodes,
        created_at=timezone.now(),
        source="k8s_nodes_and_node_metrics",
        confidence="low",
        warnings=[
            "Snapshot contains node allocatable resources and live metrics, "
            "but not scheduled pod resource requests."
        ],
    )

def build_kooplex_state_snapshot() -> ClusterResourceSnapshot:
    base = build_node_metrics_snapshot()
    requested_by_node = get_kooplex_requested_resources_by_node()

    enriched_nodes = []

    for node in base.nodes:
        requested = requested_by_node.get(node.name)

        enriched_nodes.append(
            NodeResourceState(
                name=node.name,
                allocatable_cpu_m=node.allocatable_cpu_m,
                allocatable_memory_mib=node.allocatable_memory_mib,
                allocatable_gpu=node.allocatable_gpu,
                requested_cpu_m=requested.cpu_m if requested else 0,
                requested_memory_mib=requested.memory_mib if requested else 0,
                requested_gpu=requested.gpu if requested else 0,
                live_cpu_m=node.live_cpu_m,
                live_memory_mib=node.live_memory_mib,
                unschedulable=node.unschedulable,
                labels=node.labels,
                taints=node.taints,
            )
        )

    return ClusterResourceSnapshot(
        nodes=enriched_nodes,
        created_at=timezone.now(),
        source="k8s_nodes_metrics_plus_kooplex_state",
        confidence="medium",
        warnings=[
            "Snapshot uses Kooplex-known pod state instead of a full Kubernetes pod listing."
        ],
    )
