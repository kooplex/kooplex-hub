from dataclasses import dataclass

from django.db import transaction

from container.models import Container


class ContainerActionError(RuntimeError):
    pass


@dataclass
class RuntimeActionResult:
    message: str
    level: str = "info"


def request_container_action(
    *,
    container, 
    action, 
    actor
):
    if action == "start":
        return request_start(
            container, 
            actor,
        )

    if action == "stop":
        return request_stop(
            container, 
            actor,
        )

    if action == "restart":
        return request_restart(
            container=container,
            actor=actor,
        )

    raise ContainerActionError(
        f"Unknown container action: {action}"
    )


def request_start(
    *,
    container,
    actor,
):
    from container.tasks import start_container

    with transaction.atomic():
        container = (
            Container.objects
            .select_for_update()
            .get(
                pk=container.pk,
                user=actor,
            )
        )

        if container.state not in {
            Container.State.NOTPRESENT,
            Container.State.ERROR,
        }:
            raise ContainerActionError(
                "Environment cannot be started "
                "from its current state."
            )

        container.require_running = True
        container.restart_reasons = ""
        container.state = Container.State.STARTING

        container.save(
            update_fields=[
                "require_running",
                "restart_reasons",
                "state",
            ]
        )

        container_id = container.pk

        transaction.on_commit(
            lambda: start_container(container_id)
        )

    return RuntimeActionResult(
        message=(
            f"Starting environment "
            f"'{container.name}'."
        ),
        level="success",
    )


def _request_container_stop(
    *,
    container,
):
    from container.tasks import stop_container

    with transaction.atomic():
        container = (
            Container.objects
            .select_for_update()
            .get(pk=container.pk)
        )

        if container.state not in {
            Container.State.STARTING,
            Container.State.RUNNING,
            Container.State.NEED_RESTART,
            Container.State.ERROR,
        }:
            raise ContainerActionError(
                "Environment cannot be stopped "
                "from its current state."
            )

        container.require_running = False
        container.restart_reasons = ""
        container.state = Container.State.STOPPING

        container.cpu_usage_m = None
        container.memory_usage_mib = None
        container.resource_usage_at = None
        container.idle = None

        container.save(
            update_fields=[
                "require_running",
                "restart_reasons",
                "state",
                "cpu_usage_m",
                "memory_usage_mib",
                "resource_usage_at",
                "idle",
            ]
        )

        container_id = container.pk

        transaction.on_commit(
            lambda: stop_container(container.pk)
        )

    return container.pk


def request_stop(
    *,
    container,
    actor,
):
    if container.user_id != actor.pk:
        raise ContainerActionError(
            "You cannot stop this environment."
        )

    stopped_id = _request_container_stop(
        container_id=container.pk,
    )

    if stopped_id is None:
        raise ContainerActionError(
            "Environment cannot be stopped "
            "from its current state."
        )

    return RuntimeActionResult(
        message=(
            f"Stopping environment "
            f"'{container.name}'."
        ),
        level="warning",
    )


def request_stop_automatically(
    *,
    container_id,
    reason,
):
    stopped_id = _request_container_stop(
        container_id=container_id
    )

    if stopped_id is None:
        return False

    container = (
        Container.objects
        .only(
            "id",
            "name",
            "user_id",
        )
        .get(pk=stopped_id)
    )

    broadcast_container_runtime_changed(
        container=container,
        reason=reason,
        notification={
            "level": "warning",
            "message": (
                f"Environment '{container.name}' "
                "was stopped because it exceeded "
                "its idle-time limit."
            ),
        },
    )

    return True    


def request_restart(
    *,
    container,
    actor,
):
    from container.tasks import restart_container

    with transaction.atomic():
        container = (
            Container.objects
            .select_for_update()
            .get(
                pk=container.pk,
                user=actor,
            )
        )

        if container.state not in {
            Container.State.RUNNING,
            Container.State.NEED_RESTART,
        }:
            raise ContainerActionError(
                "Environment cannot be restarted "
                "from its current state."
            )

        container.require_running = True
        container.restart_reasons = ""
        container.state = Container.State.STARTING

        container.save(
            update_fields=[
                "require_running",
                "restart_reasons",
                "state",
            ]
        )

        container_id = container.pk

        transaction.on_commit(
            lambda: restart_container(container_id)
        )

    return RuntimeActionResult(
        message=(
            f"Restarting environment "
            f"'{container.name}'."
        ),
        level="warning",
    )


def mark_container_restart_required(
    *,
    container_id,
    reason,
):
    with transaction.atomic():
        container = (
            Container.objects
            .select_for_update()
            .get(pk=container_id)
        )

        if container.state not in {
            Container.State.RUNNING,
            Container.State.NEED_RESTART,
        }:
            return False

        reasons = [
            part.strip()
            for part in (
                container.restart_reasons
                or ""
            ).split(";")
            if part.strip()
        ]

        if reason not in reasons:
            reasons.append(reason)

        container.restart_reasons = (
            "; ".join(reasons)
        )
        container.state = (
            Container.State.NEED_RESTART
        )

        container.save(
            update_fields=[
                "restart_reasons",
                "state",
            ]
        )

    return True


