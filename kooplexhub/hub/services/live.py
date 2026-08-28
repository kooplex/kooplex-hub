import uuid

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def live_group_for_user(user_id):
    return f"live-user-{user_id}"


def broadcast_live_event(
    *,
    user_id,
    keys=(),
    event="object.changed",
    payload=None,
    notification=None,
):
    if not user_id:
        return

    channel_layer = get_channel_layer()

    if channel_layer is None:
        return

    message = {
        "event": event,
        "event_id": uuid.uuid4().hex,
        "keys": list(keys),
        **(payload or {}),
    }

    if notification is not None:
        message["notification"] = notification

    async_to_sync(
        channel_layer.group_send
    )(
        live_group_for_user(user_id),
        {
            "type": "live.event",
            "payload": message,
        },
    )


def broadcast_live_event_to_users(
    *,
    users,
    **kwargs,
):
    seen = set()

    for user in users:
        if user.pk in seen:
            continue

        seen.add(user.pk)

        broadcast_live_event(
            user_id=user.pk,
            **kwargs,
        )


def push_live_message(
    *,
    user_id,
    message,
    level="info",
    title=None,
):
    notification = {
        "level": level,
        "message": message,
    }

    if title:
        notification["title"] = title

    broadcast_live_event(
        user_id=user_id,
        event="notification",
        notification=notification,
    )


