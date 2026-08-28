from hub.services.live import (
    broadcast_live_event_to_users,
)


def course_live_audience(course):
    return [
        binding.user
        for binding in (
            course.userbindings
            .filter(user__is_active=True)
            .select_related("user")
        )
    ]


def course_teacher_audience(course):
    return [
        binding.user
        for binding in (
            course.userbindings
            .filter(
                is_teacher=True,
                user__is_active=True,
            )
            .select_related("user")
        )
    ]


def broadcast_course_assignments_changed(
    *,
    course,
    assignment=None,
    reason=None,
    users=None,
    notification=None,
):
    payload = {
        "model": "course",
        "id": course.pk,
    }

    if assignment is not None:
        payload["assignment_id"] = (
            assignment.pk
        )

    if reason:
        payload["reason"] = reason

    broadcast_live_event_to_users(
        users=(
            users
            if users is not None
            else course_live_audience(
                course
            )
        ),
        keys=[
            f"course-assignments:{course.pk}",
        ],
        payload=payload,
        notification=notification,
    )


