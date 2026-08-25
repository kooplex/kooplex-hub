from django import template

from ..services.editor_context import (
    make_name_editor_context,
    make_description_editor_context,
    make_image_editor_context,
    make_mounts_summary_context,
    make_member_summary_context,
)


register = template.Library()


@register.inclusion_tag(
    "ui/editors/name/display.html"
)
def course_name_editor(course, presentation):
    return {
        "editor": make_name_editor_context(
            course=course,
            presenter=presentation,
        )
    }


@register.inclusion_tag(
    "ui/editors/description/display.html"
)
def course_description_editor(
    course,
    presentation,
):
    return {
        "editor": make_description_editor_context(
            course=course,
            presenter=presentation,
        )
    }


@register.inclusion_tag(
    "ui/editors/image_picker/display.html"
)
def course_image_editor(course, presentation):
    return {
        "editor": make_image_editor_context(
            course=course,
            presenter=presentation,
        )
    }


@register.inclusion_tag(
    "ui/editors/mounts_picker/summary.html"
)
def course_mounts_editor(course, presentation):
    return {
        "editor": make_mounts_summary_context(
            course=course,
            presenter=presentation,
        )
    }


@register.inclusion_tag(
    "ui/editors/membership/summary.html"
)
def course_members_editor(course, presentation):
    return {
        "editor": make_member_summary_context(
            course=course,
            presenter=presentation,
        )
    }


