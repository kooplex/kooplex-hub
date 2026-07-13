from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Iterable, Protocol

from kubernetes.client.exceptions import ApiException

from .client import KubernetesClients
from .quantities import cpu_to_millicores, memory_to_bytes
from .types import (
    ClusterResourceSnapshot,
    NodeResourceSnapshot,
    PodResourceSnapshot,
    ResourceVector,
)

logger = logging.getLogger(__name__)
GPU_RESOURCE = "nvidia.com/gpu"
CONTAINER_ID_LABEL = "kooplex.io/container-id"


@dataclass(frozen=True)
class Inventory:
    source: str
    nodes: list[Any]
    pods: list[Any]
    warning: str | None = None


class InventoryProvider(Protocol):
    def read(self) -> Inventory: ...


class KubernetesInventoryProvider:
    def __init__(self, clients: KubernetesClients, *, node_label_selector: str = ""):
        self.clients = clients
        self.node_label_selector = node_label_selector

    def read(self) -> Inventory:
        nodes = self.clients.core.list_node(
            label_selector=self.node_label_selector or None
        ).items
        pods = self.clients.core.list_pod_for_all_namespaces(
            field_selector="status.phase!=Succeeded,status.phase!=Failed"
        ).items
        return Inventory(source="kubernetes", nodes=list(nodes), pods=list(pods))


@dataclass(frozen=True)
class ConfiguredNode:
    name: str
    allocatable_cpu_m: int
    allocatable_memory_mib: int
    allocatable_gpu: int = 0


class ConfiguredInventoryProvider:
    def __init__(self, nodes: Iterable[ConfiguredNode]):
        self.nodes = list(nodes)

    def read(self) -> Inventory:
        node_objects = [
            {
                "metadata": {"name": node.name},
                "status": {
                    "allocatable": {
                        "cpu": f"{node.allocatable_cpu_m}m",
                        "memory": f"{node.allocatable_memory_mib}Mi",
                        GPU_RESOURCE: str(node.allocatable_gpu),
                    }
                },
            }
            for node in self.nodes
        ]
        return Inventory(source="config", nodes=node_objects, pods=[])


class HybridInventoryProvider:
    """Use live inventory where RBAC permits and configured worker capacity otherwise."""

    def __init__(
        self,
        clients: KubernetesClients,
        fallback: ConfiguredInventoryProvider,
        *,
        node_label_selector: str = "",
    ):
        self.clients = clients
        self.fallback = fallback
        self.node_label_selector = node_label_selector

    def read(self) -> Inventory:
        warnings: list[str] = []
        try:
            nodes = list(
                self.clients.core.list_node(
                    label_selector=self.node_label_selector or None
                ).items
            )
            node_source = "kubernetes"
        except (ApiException, PermissionError, OSError) as exc:
            fallback = self.fallback.read()
            nodes = fallback.nodes
            node_source = "config"
            warnings.append(f"Worker-node inventory unavailable: {exc}")

        try:
            pods = list(
                self.clients.core.list_pod_for_all_namespaces(
                    field_selector="status.phase!=Succeeded,status.phase!=Failed"
                ).items
            )
            pod_source = "kubernetes-cluster"
        except (ApiException, PermissionError, OSError) as exc:
            warnings.append(f"Cluster-wide pod inventory unavailable: {exc}")
            try:
                pods = list(
                    self.clients.core.list_namespaced_pod(
                        namespace=self.clients.namespace,
                        field_selector="status.phase!=Succeeded,status.phase!=Failed",
                    ).items
                )
                pod_source = "kubernetes-namespace"
            except (ApiException, PermissionError, OSError) as nested:
                warnings.append(f"Namespace pod inventory unavailable: {nested}")
                pods = []
                pod_source = "unavailable"

        warning = "; ".join(warnings) or None
        if warning:
            logger.warning(warning)
        return Inventory(
            source=f"nodes={node_source},pods={pod_source}",
            nodes=nodes,
            pods=pods,
            warning=warning,
        )


class MetricsApiUsageProvider:
    def __init__(self, clients: KubernetesClients):
        self.clients = clients

    def pod_usage(self) -> dict[tuple[str, str], ResourceVector]:
        result = self.clients.custom.list_namespaced_custom_object(
            group="metrics.k8s.io",
            version="v1beta1",
            namespace=self.clients.namespace,
            plural="pods",
        )
        usage_by_pod: dict[tuple[str, str], ResourceVector] = {}
        for pod in result.get("items", []):
            total = ResourceVector()
            for container in pod.get("containers", []):
                usage = container.get("usage", {})
                total += ResourceVector(
                    cpu_m=cpu_to_millicores(usage.get("cpu", 0)),
                    memory_bytes=memory_to_bytes(usage.get("memory", 0)),
                    # metrics.k8s.io normally exposes CPU and memory, not GPU utilization.
                    gpu=0,
                )
            metadata = pod.get("metadata", {})
            usage_by_pod[(metadata.get("namespace", ""), metadata.get("name", ""))] = total
        return usage_by_pod

    def node_usage(self) -> dict[str, ResourceVector]:
        result = self.clients.custom.list_cluster_custom_object(
            group="metrics.k8s.io",
            version="v1beta1",
            plural="nodes",
        )
        return {
            item["metadata"]["name"]: ResourceVector(
                cpu_m=cpu_to_millicores(item.get("usage", {}).get("cpu", 0)),
                memory_bytes=memory_to_bytes(item.get("usage", {}).get("memory", 0)),
                gpu=0,
            )
            for item in result.get("items", [])
        }


def _get(obj: Any, *path: str, default: Any = None) -> Any:
    current = obj
    for key in path:
        if isinstance(current, dict):
            current = current.get(key, default)
        else:
            current = getattr(current, key, default)
        if current is default:
            return default
    return current


def resource_vector(resources: dict[str, Any] | None) -> ResourceVector:
    resources = resources or {}
    return ResourceVector(
        cpu_m=cpu_to_millicores(resources.get("cpu", 0)),
        memory_bytes=memory_to_bytes(resources.get("memory", 0)),
        gpu=int(resources.get(GPU_RESOURCE, 0) or 0),
    )


def container_requests(container: Any) -> ResourceVector:
    requests = _get(container, "resources", "requests", default={}) or {}
    return resource_vector(requests)


def pod_requests(pod: Any) -> ResourceVector:
    containers = list(_get(pod, "spec", "containers", default=[]) or [])
    regular = ResourceVector.sum([container_requests(item) for item in containers])

    init_containers = list(_get(pod, "spec", "init_containers", default=None) or _get(pod, "spec", "initContainers", default=[]) or [])
    init_max = ResourceVector()
    for item in init_containers:
        request = container_requests(item)
        init_max = ResourceVector(
            cpu_m=max(init_max.cpu_m, request.cpu_m),
            memory_bytes=max(init_max.memory_bytes, request.memory_bytes),
            gpu=max(init_max.gpu, request.gpu),
        )

    overhead = resource_vector(_get(pod, "spec", "overhead", default={}) or {})
    return ResourceVector(
        cpu_m=max(regular.cpu_m, init_max.cpu_m) + overhead.cpu_m,
        memory_bytes=max(regular.memory_bytes, init_max.memory_bytes) + overhead.memory_bytes,
        gpu=max(regular.gpu, init_max.gpu) + overhead.gpu,
    )


def node_allocatable(node: Any) -> ResourceVector:
    return resource_vector(_get(node, "status", "allocatable", default={}) or {})


class ClusterResourceCollector:
    def __init__(
        self,
        inventory_provider: InventoryProvider,
        usage_provider: MetricsApiUsageProvider | None = None,
    ):
        self.inventory_provider = inventory_provider
        self.usage_provider = usage_provider

    def collect(self) -> ClusterResourceSnapshot:
        inventory = self.inventory_provider.read()
        warning = inventory.warning

        usage_parts: list[str] = []
        pod_usage: dict[tuple[str, str], ResourceVector] = {}
        node_usage: dict[str, ResourceVector] = {}
        if self.usage_provider is not None:
            try:
                pod_usage = self.usage_provider.pod_usage()
                usage_parts.append("pods")
            except (ApiException, PermissionError, OSError, KeyError, ValueError) as exc:
                logger.warning("Pod metrics unavailable: %s", exc)
                warning = warning or f"Pod metrics unavailable: {exc}"
            try:
                node_usage = self.usage_provider.node_usage()
                usage_parts.append("nodes")
            except (ApiException, PermissionError, OSError, KeyError, ValueError) as exc:
                logger.warning("Node metrics unavailable: %s", exc)
                warning = warning or f"Node metrics unavailable: {exc}"
        usage_source = (
            f"metrics.k8s.io:{','.join(usage_parts)}" if usage_parts else "unavailable"
        )

        nodes_by_name = {
            _get(node, "metadata", "name"): node
            for node in inventory.nodes
            if _get(node, "metadata", "name")
        }
        requested_by_node = {name: ResourceVector() for name in nodes_by_name}
        pod_snapshots: list[PodResourceSnapshot] = []

        aggregate_requested = ResourceVector()
        for pod in inventory.pods:
            namespace = _get(pod, "metadata", "namespace", default="")
            name = _get(pod, "metadata", "name", default="")
            node_name = _get(pod, "spec", "node_name")
            requested = pod_requests(pod)
            if node_name in requested_by_node:
                requested_by_node[node_name] += requested
                aggregate_requested += requested
            elif node_name is None:
                # Pending pods are a cluster-wide commitment but cannot be assigned
                # to an individual node yet.
                aggregate_requested += requested

            labels = _get(pod, "metadata", "labels", default={}) or {}
            if CONTAINER_ID_LABEL in labels:
                pod_snapshots.append(
                    PodResourceSnapshot(
                        name=name,
                        namespace=namespace,
                        node=node_name,
                        phase=_get(pod, "status", "phase"),
                        container_id=labels.get(CONTAINER_ID_LABEL),
                        requested=requested,
                        usage=pod_usage.get((namespace, name)),
                    )
                )

        node_snapshots: list[NodeResourceSnapshot] = []
        for name, node in nodes_by_name.items():
            allocatable = node_allocatable(node)
            requested = requested_by_node[name]
            node_snapshots.append(
                NodeResourceSnapshot(
                    name=name,
                    allocatable=allocatable,
                    requested=requested,
                    available=allocatable - requested,
                    usage=node_usage.get(name),
                )
            )

        allocatable_total = ResourceVector.sum([item.allocatable for item in node_snapshots])
        requested_total = aggregate_requested
        return ClusterResourceSnapshot(
            inventory_source=inventory.source,
            usage_source=usage_source,
            allocatable=allocatable_total,
            requested=requested_total,
            available=allocatable_total - requested_total,
            nodes=node_snapshots,
            pods=pod_snapshots,
            warning=warning,
        )
