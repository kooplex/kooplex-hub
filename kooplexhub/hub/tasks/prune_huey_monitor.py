import logging

from django.core.management import call_command
from django.db import close_old_connections
from django_huey import get_queue
from huey import crontab
from huey.exceptions import TaskLockedException

logger = logging.getLogger("kooplex.huey.diagnostics")

hub_queue = get_queue("hub")


@hub_queue.periodic_task(crontab(hour=3, minute=0))
@hub_queue.lock_task("prune-huey-monitor")
def periodic_prune_huey_monitor():
    """
    Daily cleanup of historical Huey Monitor records.
    """

    logger.info("Starting periodic Huey Monitor cleanup")

    close_old_connections()

    try:
        call_command(
            "prune_huey_monitor",
            days=30,
            batch_size=200,
            max_batches=20,
            apply=True,
        )

        logger.info("Periodic Huey Monitor cleanup completed")

    except Exception:
        logger.exception("Periodic Huey Monitor cleanup failed")
        raise

    finally:
        close_old_connections()

