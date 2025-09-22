from django import template
from django.template.loader import render_to_string


register = template.Library()

@register.simple_tag
def render_name(course):
    return render_to_string('hub/widgets/inline_textfield.html', {'model': 'course', 'attr': 'name', 'obj': course, 'value': course.name, 'editable': True})

@register.simple_tag
def render_description(course):
    return render_to_string('hub/widgets/inline_textarea.html', {'model': 'course', 'obj': course, 'editable': True})

@register.simple_tag
def render_volumes(course, user):
    return render_to_string("volume/tables/volumes.html", {'model': 'course', 'pk': course.id, 'volumes': course.volumes, 'user': user })

@register.simple_tag
def render_busy(tab):
    return render_to_string('education/assignment/busy.html', { 'tab': tab })

