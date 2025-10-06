from django import template
from django.template.loader import render_to_string


register = template.Library()

@register.simple_tag
def render_name(container = None, **kwargs):
    return render_to_string('hub/widgets/inline_textfield.html', {
        'model': 'container', 'attr': 'name', 'pk': getattr(container, 'pk', None), 'value': getattr(container, 'name', kwargs.get('value')), 'editable': True,
        'error': kwargs.get('error', None), 'original_value': kwargs.get('original_value')
    })



