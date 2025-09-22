from django import template
from django.template.loader import render_to_string


register = template.Library()

@register.simple_tag
def render_name(container):
    return render_to_string('hub/widgets/inline_textfield.html', {'model': 'container', 'attr': 'name', 'obj': container, 'value': container.name, 'editable': True})



