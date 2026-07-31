from django import template

from ..services.project_presenter import (
    ProjectPresenter,
)

register = template.Library()


@register.simple_tag(takes_context=True)
def present_project(context, project):
    return ProjectPresenter(
        project=project,
        user=context["request"].user,
    )
