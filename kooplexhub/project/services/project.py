from django.db.models import Q

from ..models import (
    Project,
    UserProjectBinding,
)


def get_project_creator_binding(project):
    return (
        project.userbindings
        .select_related("user")
        .get(
            role=UserProjectBinding.Role.CREATOR,
        )
    )


def get_project_creator(project):
    return get_project_creator_binding(
        project
    ).user


def get_joinable_projects_for_user(user):
    return (
        Project.objects
        .joinable_by(user)
        .prefetch_related(
            "userbindings__user",
        )
        .order_by("name")
    )
