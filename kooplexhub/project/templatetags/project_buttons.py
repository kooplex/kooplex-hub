from django import template
from django.utils.html import format_html
from django.template.loader import render_to_string
from django.urls import reverse

register = template.Library()


@register.simple_tag
def project_creator(project = None, user = None):
    return format_html(f"""
<p class="card-text mb-2"><strong>Creator:</strong> {project.creator.profile.name_and_username}</p>
    """) if project and project.creator != user else ""


@register.simple_tag
def project_scope(project = None):
    return render_to_string("widgets/button_scope.html", {'project':project})


