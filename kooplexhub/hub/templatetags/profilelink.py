from django import template
from django.utils.html import format_html
from django.urls import reverse

register = template.Library()

from kooplexhub.settings import URL_PROFILE

@register.simple_tag
def profilelink(*args, **kwargs):
    return format_html(f"""<li><a class="dropdown-item" href="{URL_PROFILE}" data-toggle="modal" data-target="#profile">Profile</a></li>""")

