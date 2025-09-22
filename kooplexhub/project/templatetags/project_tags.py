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
def render_volumes(project, user):
    return render_to_string("volume/tables/volumes.html", {'model': 'project', 'pk': project.id, 'volumes': project.volumes, 'user': user })
