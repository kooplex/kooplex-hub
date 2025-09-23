from django import template
from django.template.loader import render_to_string


register = template.Library()

@register.simple_tag
def render_name(project, user):
    return render_to_string('hub/widgets/inline_textfield.html', {'model': 'project', 'attr': 'name', 'obj': project, 'value': project.name, 'editable': project.is_admin(user)})

@register.simple_tag
def render_description(project, user):
    return render_to_string('hub/widgets/inline_textarea.html', {'model': 'project', 'obj': project, 'editable': project.is_admin(user)})

@register.simple_tag
def render_volumes(project, user, **kwargs):
    from volume.models import Volume
    volumes=getattr(project, 'volumes', Volume.objects.filter(pk__in=kwargs.get('value', [])))
    return render_to_string("volume/tables/volumes.html", {
        'model': 'project', 
        'pk': getattr(project, 'pk', None), 
        'volumes': volumes, 
        'value': list(map(lambda v: v.id, volumes)),
        'user': user, 
    })
