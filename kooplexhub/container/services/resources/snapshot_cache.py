import logging
from django.core.cache import cache
from django.utils import timezone

from .k8s_snapshot import build_kooplex_state_snapshot

logger = logging.getLogger(__name__)


CACHE_KEY = "kooplex:cluster_resource_snapshot"
ERROR_KEY = "kooplex:cluster_resource_snapshot:last_error"
LOCK_KEY = "kooplex:cluster_resource_snapshot:refresh_lock"

SNAPSHOT_TIMEOUT_SECONDS = 120
LOCK_TIMEOUT_SECONDS = 20


def refresh_cluster_resource_snapshot():
    """
    Called by a periodic task, management command, or manual shell test.
    """
    if not cache.add(LOCK_KEY, "1", timeout=LOCK_TIMEOUT_SECONDS):
        logger.info("Resource snapshot refresh skipped: lock already held")
        return cache.get(CACHE_KEY)

    try:
        snapshot = build_kooplex_state_snapshot()
        cache.set(CACHE_KEY, snapshot, timeout=SNAPSHOT_TIMEOUT_SECONDS)
        cache.delete(ERROR_KEY)
        return snapshot
    except Exception as exc:
        logger.exception(f"Failed to refresh cluster resource snapshot -- {exc}")
        cache.set(ERROR_KEY, str(exc), timeout=SNAPSHOT_TIMEOUT_SECONDS)
        raise
    finally:
        cache.delete(LOCK_KEY)


def get_latest_cluster_resource_snapshot():
    snapshot = cache.get(CACHE_KEY)

    if snapshot is None:
        snapshot = refresh_cluster_resource_snapshot()

    return snapshot


def get_last_snapshot_error():
    return cache.get(ERROR_KEY)


def snapshot_age_seconds(snapshot) -> int | None:
    if not snapshot:
        return None

    return int((timezone.now() - snapshot.created_at).total_seconds())
