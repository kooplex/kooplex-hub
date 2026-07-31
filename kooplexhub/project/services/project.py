from ..models import UserProjectBinding


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
