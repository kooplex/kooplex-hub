import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from container.consumers import ContainerLiveConsumer

logger = logging.getLogger(__name__)


def broadcast_container_live_event(user, keys, payload=None):
    if user is None or not user.is_authenticated:
        logger.debug("Skipping live event: missing/anonymous user")
        return

    channel_layer = get_channel_layer()

    if channel_layer is None:
        logger.warning("Skipping live event: no channel layer configured")
        return

    event_payload = {
        "event": "object.changed",
        "keys": list(keys),
        **(payload or {}),
    }

    group_name = ContainerLiveConsumer.group_name_for_user(user.pk)

    logger.debug(
        "Broadcasting live event to %s: %s",
        group_name,
        event_payload,
    )

    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            "type": "container.live_event",
            "payload": event_payload,
        },
    )


def broadcast_container_runtime_changed(
    container,
    actor=None,
    reason=None,
    backend_state=None,
    audience=None,
):
    """
    Broadcast that runtime-dependent widgets for this container should refresh.

    actor is optional:
      - HTMX views can pass request.user
      - watcher/shell can omit it

    actor is metadata, not authorization.
    """

    payload = {
        "event": "container.runtime.changed",
        "model": "container",
        "id": container.pk,
    }

    if reason:
        payload["reason"] = reason

    if backend_state:
        payload["backend_state"] = backend_state

    if actor is not None and getattr(actor, "is_authenticated", False):
        payload["actor_id"] = actor.pk

    keys = [
        f"container-runtime:{container.pk}",
        f"container:{container.pk}",
    ]

    users = audience or get_container_runtime_audience(container)

    for user in users:
        broadcast_container_live_event(
            user=user,
            keys=keys,
            payload=payload,
        )


def get_container_runtime_audience(container):
    """
    Users whose open pages may contain runtime widgets for this container.

    For now: owner only.
    Later: add project/course members if those pages show container shortcuts.
    """

    users = []

    if container.user_id:
        users.append(container.user)

    return [
        user
        for user in users
        if user is not None and user.is_active
    ]

