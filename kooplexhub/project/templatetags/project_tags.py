from django import template
from django.template.loader import render_to_string


register = template.Library()

@register.simple_tag
def render_name(project, user, **kwargs):
    e = project.is_admin(user) if project else True
    return render_to_string('hub/widgets/inline_textfield.html', {'model': 'project', 'attr': 'name', 'pk': getattr(project, 'pk', None), 'value': getattr(project, 'name', kwargs.get('value')), 'editable': e})

@register.simple_tag
def render_description(project, user, **kwargs):
    e = project.is_admin(user) if project else True
    return render_to_string('hub/widgets/inline_textarea.html', {'model': 'project', 'pk': getattr(project, 'pk', None), 'value': getattr(project, 'description', kwargs.get('value')), 'editable': e})

@register.simple_tag
def render_volumes(project, user, **kwargs):
    from volume.models import Volume
    volumes=getattr(project, 'volumes', Volume.objects.filter(pk__in=kwargs.get('value', [])))#FIXME auth
    return render_to_string("volume/tables/volumes.html", {
        'model': 'project', 
        'pk': getattr(project, 'pk', None), 
        'volumes': volumes, 
        'value': list(map(lambda v: v.id, volumes)),
        'user': user, 
        'editable': kwargs.get('is_admin'),
    })
