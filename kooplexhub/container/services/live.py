from hub.services.live import (
    broadcast_live_event_to_users,
)


def get_container_runtime_audience(
    container,
):
    if (
        container.user_id
        and container.user.is_active
    ):
        return [container.user]

    return []


def broadcast_container_runtime_changed(
    container,
    *,
    actor=None,
    reason=None,
    backend_state=None,
    audience=None,
):
    payload = {
        "model": "container",
        "id": container.pk,
    }

    if reason:
        payload["reason"] = reason

    if backend_state:
        payload["backend_state"] = (
            backend_state
        )

    users = (
        audience
        or get_container_runtime_audience(
            container
        )
    )

    broadcast_live_event_to_users(
        users=users,
        keys=[
            f"container-runtime:{container.pk}",
        ],
        payload=payload,
    )


