from dataclasses import dataclass

from django.db import transaction

from container.models import Container


@dataclass
class RuntimeActionResult:
    message: str
    level: str = "info"


def request_container_action(container, action, actor):
    if action == "start":
        return request_start(container, actor)

    if action == "stop":
        return request_stop(container, actor)

    raise ValueError(f"Unknown container action: {action}")


def request_start(container, actor):
    with transaction.atomic():
        container.require_running = True

        if container.state in {
            Container.State.NOTPRESENT,
            Container.State.ERROR,
        }:
            container.state = Container.State.STARTING

        container.save(
            update_fields=[
                "require_running",
                "state",
            ]
        )

        # Later:
        # enqueue/start Kubernetes operation, or let watcher/reconciler observe require_running.

    return RuntimeActionResult(
        message=f"Starting environment '{container.name}'.",
        level="success",
    )


def request_stop(container, actor):
    with transaction.atomic():
        container.require_running = False

        if container.state in {
            Container.State.RUNNING,
            Container.State.NEED_RESTART,
            Container.State.ERROR,
        }:
            container.state = Container.State.STOPPING

        container.save(
            update_fields=[
                "require_running",
                "state",
            ]
        )

        # Later:
        # enqueue/stop Kubernetes operation, or let watcher/reconciler observe require_running.

    return RuntimeActionResult(
        message=f"Stopping environment '{container.name}'.",
        level="warning",
    )
