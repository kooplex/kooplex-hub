from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from django.core.cache import cache
from django.utils.dateparse import parse_datetime
from django_huey import db_periodic_task
from huey import crontab

from container.models import Container
from container.services.kubernetes.metrics import ClusterResourceCollector
from container.services.kubernetes.model_usage import usage_to_model_values
from container.services.kubernetes.types import ResourceVector
from container.services.kubernetes.wiring import build_cluster_resource_collector

SNAPSHOT_KEY = "kooplex:kubernetes:resource-snapshot"
LOCK_KEY = f"{SNAPSHOT_KEY}:lock"


@db_periodic_task(
    crontab(minute="*"),
    queue="container",
)
def refresh_cluster_resource_snapshot() -> None:
    """Refresh cluster capacity and live Kooplex Pod usage.

    ``ResourceVector`` deliberately uses bytes internally for Kubernetes
    arithmetic. Model fields deliberately use MiB. Conversion happens only at
    this persistence boundary.
    """
    if not cache.add(LOCK_KEY, "1", timeout=55):
        return

    try:
        collector: ClusterResourceCollector = build_cluster_resource_collector()
        snapshot = collector.collect()
        cache.set(SNAPSHOT_KEY, snapshot.to_dict(), timeout=180)

        # A rollout can temporarily expose two Pods for one logical Container.
        # Sum their live usage rather than letting arbitrary list order choose one.
        usage_by_container_id: dict[int, ResourceVector] = defaultdict(ResourceVector)
        for pod in snapshot.pods:
            if not pod.container_id or pod.usage is None:
                continue
            try:
                container_id = int(pod.container_id)
            except (TypeError, ValueError):
                continue
            usage_by_container_id[container_id] += pod.usage

        if not usage_by_container_id:
            return

        observed_at: datetime | None = parse_datetime(snapshot.observed_at)
        containers = list(
            Container.objects.filter(pk__in=usage_by_container_id)
        )

        for container in containers:
            cpu_usage_m, memory_usage_mib = usage_to_model_values(
                usage_by_container_id[container.pk]
            )
            container.cpu_usage_m = cpu_usage_m
            container.memory_usage_mib = memory_usage_mib
            container.resource_usage_at = observed_at

        Container.objects.bulk_update(
            containers,
            [
                "cpu_usage_m",
                "memory_usage_mib",
                "resource_usage_at",
            ],
        )
    finally:
        cache.delete(LOCK_KEY)
