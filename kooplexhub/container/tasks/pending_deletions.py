from django_huey import db_periodic_task
from huey import crontab
from django.core.cache import cache

from container.services.lifecycle import reconcile_pending_deletions


@db_periodic_task(crontab(minute="*"), queue="container")
def process_pending_container_deletions():
    lock_key = "kooplex:container:pending-deletions:lock"
    if not cache.add(lock_key, "1", timeout=55):
        return
    try:
        reconcile_pending_deletions()
    finally:
        cache.delete(lock_key)
