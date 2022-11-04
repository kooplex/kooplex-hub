from django import template
from django.utils.html import format_html
from django.urls import reverse
import base64

register = template.Library()


@register.filter(name = 'decode')
def decode(thumbnail):
    return base64.b64encode(thumbnail).decode()
