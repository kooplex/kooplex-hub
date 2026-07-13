from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from kubernetes.client.exceptions import ApiException

from .client import KubernetesClients
from .manifests import deployment_manifest, service_manifest
from .types import BuiltWorkload

logger = logging.getLogger(__name__)


class KubernetesWorkloadRepository:
    def __init__(self, clients: KubernetesClients):
        self.clients = clients

    def apply(self, workload: BuiltWorkload) -> None:
        service = service_manifest(workload)
        if service is not None:
            self._upsert_service(workload.name, service)
        self._upsert_deployment(workload.name, deployment_manifest(workload))

    def delete(self, name: str) -> None:
        self._delete_deployment(name)
        self._delete_service(name)

    def restart(self, name: str) -> None:
        """Force a Deployment rollout without deleting its Service."""
        body = {
            "spec": {
                "template": {
                    "metadata": {
                        "annotations": {
                            "kooplex.io/restarted-at": datetime.now(timezone.utc).isoformat()
                        }
                    }
                }
            }
        }
        self.clients.apps.patch_namespaced_deployment(
            name=name,
            namespace=self.clients.namespace,
            body=body,
        )

    def delete_legacy_pod(self, name: str) -> bool:
        """Remove a pre-Deployment direct Pod during the one-time migration."""
        try:
            self.clients.core.delete_namespaced_pod(
                name=name,
                namespace=self.clients.namespace,
                grace_period_seconds=30,
            )
            return True
        except ApiException as exc:
            if exc.status == 404:
                return False
            raise

    def _upsert_deployment(self, name: str, body: dict[str, Any]) -> None:
        try:
            self.clients.apps.read_namespaced_deployment(name, self.clients.namespace)
        except ApiException as exc:
            if exc.status != 404:
                raise
            self.clients.apps.create_namespaced_deployment(self.clients.namespace, body)
            return
        self.clients.apps.patch_namespaced_deployment(name, self.clients.namespace, body)

    def _upsert_service(self, name: str, body: dict[str, Any]) -> None:
        try:
            self.clients.core.read_namespaced_service(name, self.clients.namespace)
        except ApiException as exc:
            if exc.status != 404:
                raise
            self.clients.core.create_namespaced_service(self.clients.namespace, body)
            return
        self.clients.core.patch_namespaced_service(name, self.clients.namespace, body)

    def _delete_deployment(self, name: str) -> None:
        try:
            self.clients.apps.delete_namespaced_deployment(
                name,
                self.clients.namespace,
                propagation_policy="Foreground",
            )
        except ApiException as exc:
            if exc.status != 404:
                raise

    def _delete_service(self, name: str) -> None:
        try:
            self.clients.core.delete_namespaced_service(name, self.clients.namespace)
        except ApiException as exc:
            if exc.status != 404:
                raise
