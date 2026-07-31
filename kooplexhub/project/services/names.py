from django.core.exceptions import ValidationError

from ..models import (
    Project,
    UserProjectBinding,
)

MIN_NAME_LENGTH = 3


def validate_project_name_for_creator(
    *,
    creator,
    name,
    exclude_project=None,
):
    normalized_name = name.strip()

    if not normalized_name:
        raise ValidationError(
            "Enter a project name."
        )

    if len(normalized_name) < MIN_NAME_LENGTH:
        raise ValidationError(
            f"Name must be at least "
            f"{MIN_NAME_LENGTH} characters."
        )

    projects = Project.objects.filter(
        userbindings__user=creator,
        userbindings__role=(
            UserProjectBinding.Role.CREATOR
        ),
        name__iexact=normalized_name,
    )

    if exclude_project is not None:
        projects = projects.exclude(
            pk=exclude_project.pk,
        )

    if projects.exists():
        raise ValidationError(
            f"Creator {creator.get_full_name()} "
            f"already have a project with this name."
        )

    return normalized_name


