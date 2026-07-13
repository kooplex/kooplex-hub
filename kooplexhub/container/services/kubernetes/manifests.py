from __future__ import annotations

from typing import Any

from .types import BuiltWorkload


def deployment_manifest(workload: BuiltWorkload) -> dict[str, Any]:
    return {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {
            "name": workload.name,
            "namespace": workload.namespace,
            "labels": workload.labels,
        },
        "spec": {
            "replicas": 1,
            "revisionHistoryLimit": 1,
            "strategy": {"type": "Recreate"},
            "selector": {"matchLabels": workload.pod_labels},
            "template": {
                "metadata": {"labels": workload.pod_labels},
                "spec": {**workload.pod_spec, "restartPolicy": "Always"},
            },
        },
    }


def service_manifest(workload: BuiltWorkload) -> dict[str, Any] | None:
    if not workload.service_ports:
        return None
    return {
        "apiVersion": "v1",
        "kind": "Service",
        "metadata": {
            "name": workload.name,
            "namespace": workload.namespace,
            "labels": workload.labels,
        },
        "spec": {
            "type": "ClusterIP",
            "selector": workload.pod_labels,
            "ports": workload.service_ports,
        },
    }
