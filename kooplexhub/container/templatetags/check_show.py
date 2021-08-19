import json

from django import template
from django.utils.html import format_html
from django.urls import reverse

register = template.Library()


@register.filter(name = 'show')
def check(request, container):
    if 'Shown' in request.COOKIES.keys():
        dd = json.loads(json.loads(request.COOKIES['Shown']))
    else:
        dd = []
    return "show" if container.id in dd else ""



