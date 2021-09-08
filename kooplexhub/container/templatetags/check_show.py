import json

from django import template
from django.utils.html import format_html
from django.urls import reverse

register = template.Library()


@register.filter(name = 'show')
def check(request, container):
    from ..views import _get_cookie
    shown = _get_cookie(request)
    return "show" if container.id in shown else ""



