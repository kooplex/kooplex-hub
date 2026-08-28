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

    candidate_ids = list(
        Container.objects
        .filter(
            state__in=[
                Container.State.RUNNING,
                Container.State.NEED_RESTART,
            ],
            image__imagetype=(
                Image.ImageType.PROJECT
            ),
        )
        .values_list("pk", flat=True)
    )

    containers = (
        Container.objects
        .filter(
            state__in=[
                Container.State.RUNNING,
                Container.State.NEED_RESTART,
            ],
            image__imagetype=Image.ImageType.PROJECT,
        )
        .iterator(chunk_size=100)
    )

    for container_id in candidate_ids:
        try:
            container = (
                Container.objects
                .get(pk=container_id)
            )
    
            # External operation: deliberately
            # OUTSIDE any transaction.
            last_activity = (
                activity_client
                .get_last_activity(container)
            )
    
            idle_hours = max(
                0.0,
                (
                    observed_at
                    - last_activity
                ).total_seconds()
                / 3600.0,
            )
    
            idle_limit = (
                container.requested_uptime_hours
            )
    
            if (
                idle_limit is not None
                and idle_hours > idle_limit
            ):
                logger.info(
                    "Stopping idle container %s",
                    container.pk,
                )
    
                request_stop_automatically(
                    container_id=container.pk,
                    reason="container.idle_timeout",
                )
                continue
    
            Container.objects.filter(
                pk=container.pk,
                state__in=[
                    Container.State.RUNNING,
                    Container.State.NEED_RESTART,
                ],
            ).update(
                idle=idle_hours,
            )
    
        except Container.DoesNotExist:
            continue

    except Exception:
        logger.exception(
            "Failed idle check for "
            "container %s",
            container_id,
        )

