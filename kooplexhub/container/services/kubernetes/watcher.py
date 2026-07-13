from __future__ import annotations

import logging
import time
from collections import defaultdict
from typing import Any, Callable, Iterable

from django.db import close_old_connections, connections
from django.db.models import Q
from django.utils import timezone
from kubernetes import watch
from kubernetes.client.exceptions import ApiException

from container.models import Container

from .client import KubernetesClients
from .labels import (
    container_id_from_object,
    managed_workload_selector,
    workload_name,
)
from .pod_state import (
    RuntimeObservation,
    RuntimeState,
    observe_deployment,
    observe_pod,
    select_effective_pod,
)

logger = logging.getLogger(__name__)

Feedback = Callable[[Container, str, str | None], None]
_UNSET = object()


class ResourceVersionExpired(RuntimeError):
    pass


class ManagedPodWatcher:
    """Keep Container runtime fields synchronized with Deployment-managed Pods.

    Pods are selected by the two stable Kooplex management labels and mapped to
    Django rows by ``kooplex.io/container-id``.  Pod names are intentionally not
    used: ReplicaSet-generated names change after every rollout.
    """

    def __init__(
        self,
        clients: KubernetesClients,
        *,
        feedback: Feedback | None = None,
        watch_timeout_seconds: int = 60,
        reconnect_delay_seconds: float = 5.0,
    ):
        self.clients = clients
        self.feedback = feedback
        self.watch_timeout_seconds = watch_timeout_seconds
        self.reconnect_delay_seconds = reconnect_delay_seconds
        self.label_selector = managed_workload_selector()

        self._pods_by_uid: dict[str, Any] = {}
        self._last_pod_name_by_container: dict[int, str | None] = {}

    def run_forever(self) -> None:
        logger.info(
            "Starting Kooplex Pod watcher in namespace %s with selector %s",
            self.clients.namespace,
            self.label_selector,
        )

        while True:
            try:
                resource_version = self.full_resync()
                self.watch_once(resource_version)
                # A normal watch timeout is followed by a full relist.  Besides
                # guarding against missed events, this observes final Deployment
                # deletion even when the last event was only a Pod DELETED event.
            except KeyboardInterrupt:
                raise
            except ResourceVersionExpired:
                logger.info("Kubernetes watch resourceVersion expired; relisting")
            except Exception:
                logger.exception("Kooplex Pod watcher failed; reconnecting")
                connections.close_all()
                time.sleep(self.reconnect_delay_seconds)

    def full_resync(self) -> str | None:
        """Replace the local cache from Kubernetes and reconcile relevant rows."""
        close_old_connections()

        pod_list = self.clients.core.list_namespaced_pod(
            namespace=self.clients.namespace,
            label_selector=self.label_selector,
        )
        deployment_list = self.clients.apps.list_namespaced_deployment(
            namespace=self.clients.namespace,
            label_selector=self.label_selector,
        )

        old_container_ids = self._cached_container_ids()
        self._replace_pods(getattr(pod_list, "items", None) or [])
        new_container_ids = self._cached_container_ids()

        deployments = {
            container_id: deployment
            for deployment in getattr(deployment_list, "items", None) or []
            if (container_id := container_id_from_object(deployment)) is not None
        }

        directly_affected = old_container_ids | new_container_ids | set(deployments)
        query = (
            Q(pk__in=directly_affected)
            | Q(require_running=True)
            | ~Q(state=Container.State.NOTPRESENT)
        )

        containers = (
            Container.objects.filter(query)
            .select_related("user", "image")
            .iterator(chunk_size=100)
        )
        seen_ids: set[int] = set()
        for container in containers:
            seen_ids.add(container.pk)
            self._reconcile_container(
                container,
                deployment=deployments.get(container.pk),
            )

        dangling_ids = directly_affected - seen_ids
        if dangling_ids:
            logger.warning(
                "Managed Kubernetes objects refer to missing Container ids: %s",
                sorted(dangling_ids),
            )

        metadata = getattr(pod_list, "metadata", None)
        return getattr(metadata, "resource_version", None)

    def watch_once(self, resource_version: str | None) -> str | None:
        """Consume one bounded watch stream and return the newest resourceVersion."""
        watcher = watch.Watch()
        newest_resource_version = resource_version

        stream = watcher.stream(
            self.clients.core.list_namespaced_pod,
            namespace=self.clients.namespace,
            label_selector=self.label_selector,
            resource_version=resource_version,
            timeout_seconds=self.watch_timeout_seconds,
            allow_watch_bookmarks=True,
        )

        for event in stream:
            close_old_connections()
            event_type = event.get("type")
            obj = event.get("object")

            metadata = getattr(obj, "metadata", None)
            newest_resource_version = (
                getattr(metadata, "resource_version", None)
                or newest_resource_version
            )

            if event_type == "BOOKMARK":
                continue
            if event_type == "ERROR":
                code = getattr(obj, "code", None)
                if code == 410:
                    raise ResourceVersionExpired()
                raise RuntimeError(
                    f"Kubernetes watch error {code}: "
                    f"{getattr(obj, 'message', obj)}"
                )
            if event_type not in {"ADDED", "MODIFIED", "DELETED"}:
                logger.debug("Ignoring Kubernetes watch event type %r", event_type)
                continue

            affected_ids = self._apply_pod_event(event_type, obj)
            for container_id in affected_ids:
                self._reconcile_container_id(container_id)

        return newest_resource_version

    def _replace_pods(self, pods: Iterable[Any]) -> None:
        self._pods_by_uid = {
            self._pod_key(pod): pod
            for pod in pods
            if container_id_from_object(pod) is not None
        }

    def _apply_pod_event(self, event_type: str, pod: Any) -> set[int]:
        key = self._pod_key(pod)
        previous = self._pods_by_uid.get(key)
        affected = {
            container_id
            for candidate in (previous, pod)
            if candidate is not None
            if (container_id := container_id_from_object(candidate)) is not None
        }

        if event_type == "DELETED":
            self._pods_by_uid.pop(key, None)
        else:
            self._pods_by_uid[key] = pod

        return affected

    def _reconcile_container_id(self, container_id: int) -> None:
        container = (
            Container.objects.filter(pk=container_id)
            .select_related("user", "image")
            .first()
        )
        if container is None:
            logger.warning(
                "Managed Pod refers to missing Container id %s", container_id
            )
            return
        self._reconcile_container(container)

    def _reconcile_container(
        self,
        container: Container,
        *,
        deployment: Any = _UNSET,
    ) -> None:
        pods = self._pods_for_container(container.pk)
        pod = select_effective_pod(pods)

        if pod is not None:
            observation = observe_pod(pod)
        else:
            if deployment is _UNSET:
                deployment = self._read_deployment(container)
            observation = observe_deployment(deployment)

        self._apply_observation(container, observation)

    def _read_deployment(self, container: Container) -> Any | None:
        try:
            return self.clients.apps.read_namespaced_deployment(
                name=workload_name(container),
                namespace=self.clients.namespace,
            )
        except ApiException as exc:
            if exc.status == 404:
                return None
            raise

    def _apply_observation(
        self,
        container: Container,
        observation: RuntimeObservation,
    ) -> None:
        state_new = self._django_state(observation.state)
        node_name = (
            None
            if observation.state == RuntimeState.NOTPRESENT
            else observation.node_name
        )

        persisted_changed = (
            container.state != state_new
            or container.state_backend != observation.backend_state
            or container.runtime_node != node_name
        )
        pod_changed = (
            self._last_pod_name_by_container.get(container.pk)
            != observation.pod_name
        )

        container.state = state_new
        container.state_backend = observation.backend_state
        container.runtime_node = node_name
        container.state_lastcheck_at = timezone.now()

        update_fields = [
            "state",
            "state_backend",
            "runtime_node",
            "state_lastcheck_at",
        ]

        if state_new == Container.State.RUNNING and not container.launched_at:
            container.launched_at = timezone.now()
            update_fields.append("launched_at")

        if state_new == Container.State.NOTPRESENT:
            container.cpu_usage_m = None
            container.memory_usage_mib = None
            container.idle = None
            container.resource_usage_at = None
            update_fields.extend(
                [
                    "cpu_usage_m",
                    "memory_usage_mib",
                    "resource_usage_at",
                    "idle",
                ]
            )

        container.save(update_fields=list(dict.fromkeys(update_fields)))
        self._last_pod_name_by_container[container.pk] = observation.pod_name

        if not (persisted_changed or pod_changed):
            return

        message = (
            f"Container {container.name} runtime changed: "
            f"{observation.backend_state} ({state_new})"
        )
        if observation.pod_name:
            message += f" on pod {observation.pod_name}"

        logger.info(message)
        if self.feedback is not None:
            self.feedback(container, message, observation.backend_state)

        # Deliberately no container.start() and no container.addroutes() here:
        # Deployments self-heal Pods, ensure_watcher enforces desired state, and
        # ContainerRuntimeService owns proxy route reconciliation.

    def _pods_for_container(self, container_id: int) -> list[Any]:
        return [
            pod
            for pod in self._pods_by_uid.values()
            if container_id_from_object(pod) == container_id
        ]

    def _cached_container_ids(self) -> set[int]:
        return {
            container_id
            for pod in self._pods_by_uid.values()
            if (container_id := container_id_from_object(pod)) is not None
        }

    @staticmethod
    def _pod_key(pod: Any) -> str:
        metadata = getattr(pod, "metadata", None)
        uid = getattr(metadata, "uid", None)
        name = getattr(metadata, "name", None)
        return str(uid or name)

    @staticmethod
    def _django_state(state: RuntimeState) -> Any:
        return {
            RuntimeState.STARTING: Container.State.STARTING,
            RuntimeState.RUNNING: Container.State.RUNNING,
            RuntimeState.STOPPING: Container.State.STOPPING,
            RuntimeState.NOTPRESENT: Container.State.NOTPRESENT,
            RuntimeState.ERROR: Container.State.ERROR,
        }[state]
