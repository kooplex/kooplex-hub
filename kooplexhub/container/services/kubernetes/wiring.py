"""Project-specific dependency wiring for Kooplex Kubernetes services."""
from __future__ import annotations

from typing import Any

from container.conf import CONTAINER_SETTINGS
from container.services.proxy import (
    ConfigurableHttpProxyClient,
    ProxyActivityClient,
)

from .builder import ContainerWorkloadBuilder, resource_policy_from_settings
from .client import KubernetesClients, get_kubernetes_clients
from .metrics import (
    ClusterResourceCollector,
    ConfiguredInventoryProvider,
    ConfiguredNode,
    HybridInventoryProvider,
    MetricsApiUsageProvider,
)
from .pods import PodOperations
from .repository import KubernetesWorkloadRepository
from .routes import KooplexRouteBuilder, RouteBuilderSettings
from .runtime import ContainerRuntimeService, RouteBuilder


def _setting(obj: Any, name: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def build_clients() -> KubernetesClients:
    settings = CONTAINER_SETTINGS.kubernetes
    return get_kubernetes_clients(_setting(settings, "namespace"))


def build_pod_operations() -> PodOperations:
    return PodOperations(build_clients())


def build_proxy_client() -> ConfigurableHttpProxyClient:
    settings = CONTAINER_SETTINGS.proxy
    base_url = str(_setting(settings, "url")).rstrip("/")
    routes_url = base_url if base_url.endswith("/routes") else f"{base_url}/routes"
    return ConfigurableHttpProxyClient(
        routes_url=routes_url,
        auth_token=_setting(settings, "auth_token"),
        timeout_seconds=float(_setting(settings, "timeout_seconds", 10.0)),
    )


def build_route_builder() -> KooplexRouteBuilder:
    settings = CONTAINER_SETTINGS.proxy
    return KooplexRouteBuilder(
        RouteBuilderSettings(
            endpoint_template=str(
                _setting(
                    settings,
                    "endpoint_template",
                    "http://{service}.{namespace}.svc.cluster.local:{port}",
                )
            ),
            base_path_template=_setting(settings, "base_path_template", None),
        )
    )


def build_runtime_service(
    *,
    route_builder: RouteBuilder | None = None,
    enable_proxy_routes: bool = True,
) -> ContainerRuntimeService:
    """Construct the Deployment-backed runtime service.

    Proxy routes are now owned by the runtime service. The concrete Kooplex
    route builder reads each proxy's public base path and targets the stable
    Kubernetes Service rather than a generated Deployment pod.
    """

    settings = CONTAINER_SETTINGS.kubernetes
    clients = build_clients()
    repository = KubernetesWorkloadRepository(clients)
    workload_builder = ContainerWorkloadBuilder(
        settings,
        resource_policy=resource_policy_from_settings(settings),
    )

    route_client = None
    if enable_proxy_routes:
        route_builder = route_builder or build_route_builder()
        route_client = build_proxy_client()

    return ContainerRuntimeService(
        repository=repository,
        workload_builder=workload_builder,
        route_client=route_client,
        route_builder=route_builder,
    )


def build_cluster_resource_collector() -> ClusterResourceCollector:
    settings = CONTAINER_SETTINGS.kubernetes
    clients = build_clients()

    fallback = _setting(settings, "resource_fallback", {})
    raw_nodes = _setting(fallback, "nodes", []) or []
    fallback_nodes = [
        ConfiguredNode(
            name=_setting(item, "name"),
            allocatable_cpu_m=int(_setting(item, "allocatable_cpu_m")),
            allocatable_memory_mib=int(_setting(item, "allocatable_memory_mib")),
            allocatable_gpu=int(_setting(item, "allocatable_gpu", 0)),
        )
        for item in raw_nodes
    ]
    inventory = HybridInventoryProvider(
        clients,
        ConfiguredInventoryProvider(fallback_nodes),
        node_label_selector=_setting(settings, "worker_node_selector", ""),
    )
    return ClusterResourceCollector(
        inventory_provider=inventory,
        usage_provider=MetricsApiUsageProvider(clients),
    )


def build_proxy_activity_client() -> ProxyActivityClient:
    settings = CONTAINER_SETTINGS.proxy

    check_container_path = _setting(
        settings,
        "check_container",
        None,
    )
    if not check_container_path:
        raise ValueError(
            "CONTAINER_SETTINGS.proxy.check_container is not configured"
        )

    return ProxyActivityClient(
        base_url=str(_setting(settings, "url")),
        check_container_path=str(check_container_path),
        auth_token=_setting(settings, "auth_token", None),
        timeout_seconds=float(
            _setting(settings, "timeout_seconds", 10.0)
        ),
    )

