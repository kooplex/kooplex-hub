from django import template

from ..services.editor_context import make_name_editor_context

register = template.Library()


@register.inclusion_tag(
    "ui/editors/name/editor.html",
)
def container_name_editor(container, presentation):
    return {
        "editor": make_name_editor_context(
            container=container,
            presenter=presentation,
        ),
    }


