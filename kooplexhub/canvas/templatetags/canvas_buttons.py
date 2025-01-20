from django import template
from django.utils.html import format_html

register = template.Library()


@register.simple_tag
def button_fetch_canvascourses(user):
    return format_html(f"""
<button type="button" class="btn btn-secondary btn-sm rounded rounded-5 border border-2 border-dark" data-bs-toggle="modal" data-bs-target="#canvascoursesModal" data-id="{user.id}">
    <i class="bi bi-boxes pe-1"></i>
    Retrieve canvas courses...
</button>
    """)


@register.filter
def canvas_tail(value):
    #FIXME: use regular expression defined in settings.py
    return value.split(" - ")[-1]
