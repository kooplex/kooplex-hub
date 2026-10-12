import logging
import os
import time

logger = logging.getLogger("kooplex.huey.diagnostics")


def report_backlog(huey, queue_name):
    start = time.monotonic()

    try:
        pending = huey.pending_count()
        scheduled = huey.scheduled_count()
        results = huey.result_count()

        elapsed = time.monotonic() - start

        message = (
            "Huey queue=%s pid=%s "
            "pending=%d scheduled=%d results=%d "
            "query_duration=%.3fs"
        )

        args = (
            queue_name,
            os.getpid(),
            pending,
            scheduled,
            results,
            elapsed,
        )

        if pending:
            logger.warning(message, *args)
        else:
            logger.info(message, *args)

    except Exception:
        logger.exception(
            "Failed to inspect Huey queue=%s",
            queue_name,
        )

