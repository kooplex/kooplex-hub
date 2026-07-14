from __future__ import annotations

import logging

from django.utils import timezone
from django_huey import (
    db_periodic_task, 
    lock_task,
)
from huey import crontab

from container.models import Container, Image
from container.services.kubernetes.wiring import (
    build_proxy_activity_client,
)

logger = logging.getLogger(__name__)


@db_periodic_task(
    crontab(minute="55"),
    queue="container",
)
@lock_task(
    "container-kill-idle",
    queue="container",
)
def kill_idle() -> None:
    """Stop project containers that exceeded their idle-time limit."""

    activity_client = build_proxy_activity_client()
    observed_at = timezone.now()

    containers = (
        Container.objects
        .filter(
            state__in=[
                Container.State.RUNNING,
                Container.State.NEED_RESTART,
            ],
            image__imagetype=Image.ImageType.PROJECT,
        )
        .select_related("user", "image")
        .iterator(chunk_size=100)
    )

    for container in containers:
        try:
            last_activity = activity_client.get_last_activity(container)

            idle_hours = max(
                0.0,
                (observed_at - last_activity).total_seconds() / 3600.0,
            )

            idle_limit = container.requested_uptime_hours

            if idle_limit is not None and idle_hours > idle_limit:
                logger.info(
                    "Stopping idle container %s belonging to %s: "
                    "%.2f hours idle, limit %.2f hours",
                    container.name,
                    container.user.username,
                    idle_hours,
                    idle_limit,
                )

                # This updates the model state and enqueues stop_container.
                container.stop()
                continue

            container.idle = idle_hours
            container.save(update_fields=["idle"])

            # Retain this if the old progress-bar cache/update mechanism
            # is still needed.
            render_progressbar(container, "idle")

        except Exception:
            # Failure to retrieve activity must never be interpreted as
            # inactivity. Leave the container running.
            logger.exception(
                "Failed to check activity for container %s belonging to %s",
                container.name,
                container.user.username,
            )

