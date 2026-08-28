from hub.services.live import (
    broadcast_live_event,
)


def broadcast_project_list_changed(
    *,
    user_ids,
    reason=None,
):
    for user_id in set(user_ids):
        broadcast_live_event(
            user_id=user_id,
            keys=[
                f"project-list:user:{user_id}",
            ],
            payload={
                "model": "project-list",
                "reason": reason,
            },
        )


def broadcast_project_changed(
    *,
    project_id,
    user_ids,
    reason=None,
):
    for user_id in set(user_ids):
        broadcast_live_event(
            user_id=user_id,
            keys=[
                f"project:{project_id}",
            ],
            payload={
                "model": "project",
                "id": project_id,
                "reason": reason,
            },
        )
