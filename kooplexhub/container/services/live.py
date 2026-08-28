from hub.services.live import (
    broadcast_live_event,
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


