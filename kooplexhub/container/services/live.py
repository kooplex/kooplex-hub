from hub.services.live import (
    broadcast_live_event,
)


def broadcast_container_changed(
    *,
    container_id,
    user_id,
    reason=None,
):
    payload = {
        "model": "container",
        "id": container_id,
    }

    if reason:
        payload["reason"] = reason

    broadcast_live_event(
        user_id=user_id,
        keys=[
            f"container:{container_id}",
        ],
        payload=payload,
    )


def broadcast_container_runtime_changed(
    container,
    *,
    reason=None,
    backend_state=None,
    notification=None,
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

    broadcast_live_event(
        user_id=container.user_id,
        keys=[
            f"container-runtime:{container.pk}",
        ],
        payload=payload,
        notification=notification,
    )


def broadcast_container_list_changed(
    *,
    user_id,
    reason=None,
    notification=None,
):
    payload = {
        "model": "container-list",
        "user_id": user_id,
    }

    if reason:
        payload["reason"] = reason

    broadcast_live_event(
        user_id=user_id,
        keys=[
            f"container-list:user:{user_id}",
        ],
        payload=payload,
        notification=notification,
    )



