from django import template

from ..models import UserProjectBinding
from ..services.editor_context import (
    make_name_editor_context,
    make_description_editor_context,
    make_image_editor_context,
    make_member_summary_context,
    make_mounts_editor_context,
)

register = template.Library()


@register.inclusion_tag(
    "ui/editors/name/display.html"
)
def project_name_editor(project, presentation):
    return {
        "editor": make_name_editor_context(
            project=project,
            presenter=presentation,
        )
    }


@register.inclusion_tag(
    "ui/editors/description/display.html"
)
def project_description_editor(project, presentation):
    return {
        "editor": make_description_editor_context(
            project=project,
            presenter=presentation,
        )
    }


@register.inclusion_tag(
    "ui/editors/image_picker/display.html"
)
def project_image_editor(project, presentation):
    return {
        "editor": make_image_editor_context(
            project=project,
            presenter=presentation,
        )
    }


@register.inclusion_tag(
    "ui/editors/membership/summary.html"
)
def project_members_editor(project, presentation):
    return {
        "editor": make_member_summary_context(
            project=project,
            presenter=presentation,
        )
    }


@register.inclusion_tag(
    "ui/editors/mounts_picker/display.html"
)
def project_mounts_editor(project, presentation):
    return {
        "editor": make_mounts_editor_context(
            project=project,
            presenter=presentation,
        )
    }


