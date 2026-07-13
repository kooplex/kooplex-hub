from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

from .labels import workload_labels, workload_name
if TYPE_CHECKING:
    from .repository import KubernetesWorkloadRepository
from .types import BuiltWorkload, RouteSpec


class WorkloadBuilder(Protocol):
    def build(self, container: Any) -> BuiltWorkload: ...


class RouteClient(Protocol):
    def add_route(self, base_path: str, endpoint: str) -> None: ...
    def remove_route(self, base_path: str) -> None: ...


class RouteBuilder(Protocol):
    def build(self, container: Any, workload: BuiltWorkload) -> list[RouteSpec]: ...


class ContainerRuntimeService:
    """Orchestrate desired Kubernetes workload state and external proxy routes."""

    def __init__(
        self,
        repository: "KubernetesWorkloadRepository",
        workload_builder: WorkloadBuilder,
        *,
        route_client: RouteClient | None = None,
        route_builder: RouteBuilder | None = None,
    ):
        self.repository = repository
        self.workload_builder = workload_builder
        self.route_client = route_client
        self.route_builder = route_builder

    def start(self, container: Any, *, remove_legacy_pod: bool = False) -> BuiltWorkload:
        workload = self.workload_builder.build(container)
        # Validate/format routes before mutating Kubernetes. A missing base path
        # should fail fast rather than leave a half-started workload.
        routes = self._routes(container, workload)

        if remove_legacy_pod:
            self.repository.delete_legacy_pod(workload.name)
        self.repository.apply(workload)
        for route in routes:
            self.route_client.add_route(route.base_path, route.endpoint)  # type: ignore[union-attr]
        return workload

    def stop(self, container: Any) -> None:
        placeholder = self._placeholder(container)
        routes = self._routes(container, placeholder)

        # Stop sending new traffic before deleting the workload.
        for route in routes:
            self.route_client.remove_route(route.base_path)  # type: ignore[union-attr]
        self.repository.delete(placeholder.name)

    def restart(self, container: Any) -> BuiltWorkload:
        """Reconcile desired state and force a new Deployment pod.

        The Service and proxy routes remain in place. With the Deployment's
        ``Recreate`` strategy there is still only one user pod at a time.
        """

        workload = self.workload_builder.build(container)
        routes = self._routes(container, workload)
        self.repository.apply(workload)
        for route in routes:
            self.route_client.add_route(route.base_path, route.endpoint)  # type: ignore[union-attr]
        self.repository.restart(workload.name)
        return workload

    def _placeholder(self, container: Any) -> BuiltWorkload:
        labels = workload_labels(container)
        # The route builder also validates service ports. Rebuilding the workload
        # here keeps stop symmetric with start and avoids duplicating proxy/domain
        # logic in a second placeholder representation.
        try:
            return self.workload_builder.build(container)
        except Exception:
            # Workload deletion must remain possible even when a now-invalid
            # image/domain configuration prevents a complete build. Routes can
            # only be removed in this fallback when proxy routing is disabled.
            if self.route_client is not None and self.route_builder is not None:
                raise
            return BuiltWorkload(
                name=workload_name(container),
                namespace=self.repository.clients.namespace,
                labels=labels,
                pod_labels=labels,
                pod_spec={},
                service_ports=[],
            )

    def _routes(self, container: Any, workload: BuiltWorkload) -> list[RouteSpec]:
        if self.route_client is None or self.route_builder is None:
            return []
        return self.route_builder.build(container, workload)
