from django import template
from django.utils.html import format_html

register = template.Library()


@register.filter
def canvas_digest(value):
    #FIXME: use regular expression defined in settings.py
    import re
    return '_'.join(re.split(r'(\d{4}).(\d{2}).* - (.*)', value)[1:-1])
