from hub.services.live import (
    broadcast_live_event,
)


def _unique_ids(user_ids):
    return tuple({
        int(user_id)
        for user_id in user_ids
        if user_id
    })


def project_member_user_ids(project):
    return tuple(
        project.userbindings.values_list(
            "user_id",
            flat=True,
        )
    )


def broadcast_project_list_changed(
    *,
    user_ids,
    reason=None,
):
    for user_id in _unique_ids(user_ids):
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
    notification=None,
):
    for user_id in _unique_ids(user_ids):
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
            notification=notification,
        )


