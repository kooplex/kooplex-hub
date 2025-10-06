from django import template
from django.template.loader import render_to_string


register = template.Library()

@register.simple_tag
def render_name(course=None, **kwargs):
    return render_to_string('hub/widgets/inline_textfield.html', {'model': 'course', 'attr': 'name', 'pk': getattr(course, 'pk', None), 'value': getattr(course, 'name', kwargs.get('value')), 'editable': True,
        'error': kwargs.get('error', None), 'original_value': kwargs.get('original_value')
    })

@register.simple_tag
def render_description(course=None, **kwargs):
    return render_to_string('hub/widgets/inline_textarea.html', {'model': 'course', 'pk': getattr(course, 'pk', None), 'editable': True, 'value': getattr(course, 'description', kwargs.get('value')),
        'error': kwargs.get('error', None), 'original_value': kwargs.get('original_value')
    })

@register.simple_tag
def render_volumes(course, user, **kwargs):
    from volume.models import Volume
    volumes=getattr(course, 'volumes', Volume.objects.filter(pk__in=kwargs.get('value', [])))#FIXME authorize
    return render_to_string("volume/tables/volumes.html", {
        'model': 'course', 
        'pk': getattr(course, 'pk', None), 
        'volumes': volumes, 
        'value': list(map(lambda v: v.id, volumes)),
        'user': user, 
        'editable': True, 
    })

@register.simple_tag
def render_busy(tab):
    return render_to_string('education/assignment/busy.html', { 'tab': tab })

