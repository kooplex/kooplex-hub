from django import template
from django.utils.html import format_html
from django.urls import reverse

from hub.templatetags.extras import render_user

register = template.Library()


@register.simple_tag
def scope(project):
    if project.scope == project.SCP_PRIVATE:
        return format_html(f"""
<i class="oi oi-key ms-1" aria-hidden="true" data-bs-toggle="tooltip" title="Private project" data-placement="top"></i>
        """)
    else:
        return format_html(f"""
<i class="oi oi-cloud ms-1" aria-hidden="true" data-bs-toggle="tooltip" title="Public project" data-placement="top"></i>
        """)


@register.simple_tag
def icon_collaborator(project, user):
    upbs = project.userprojectbindings
    c = "Collaborators: " + ", ".join([ f"{upb.user.first_name} {upb.user.last_name}" for upb in upbs if upb.user != user ])
    return format_html(f"""
<span aria-hidden="true" data-toggle="tooltip" title="{c}" data-placement="bottom">
  <i class="oi oi-people ms-1"></i>: {len(upbs)-1}
</span>
    """) if len(upbs) > 1 else ""


@register.simple_tag
def list_collaborator(project, user):
    upbs = project.userprojectbindings
    if len(upbs) > 1:
        return format_html(", ".join([ render_user(upb.user) for upb in upbs if upb.user != user ]))
    else:
        return ""


@register.simple_tag
def button_project_conf(project, enabled):
    if enabled:
        link = reverse('project:configure', args = [ project.id ])
        return format_html(f"""
<a href="{link}" role="button" class="btn btn-secondary btn-sm"><span class="oi oi-wrench" aria-hidden="true" data-toggle="tooltip" title="Settings of project {project.name}. You can modify collaboration and bind environments." data-placement="top" ></span></a>
        """)
    else:
        return format_html(f"""
<a href="#" role="button" class="btn btn-secondary btn-sm disabled"><span class="oi oi-wrench" aria-hidden="true" data-toggle="tooltip" title="You don't have permission to configure project {project.name}." data-placement="top" ></span></a>
        """)



@register.simple_tag
def button_project_hide(project, hidden):
    if hidden:
        tooltip = f'You can unhide {project.name} to show in your your list.'
        icon = 'bi bi-eye'
    else:
        tooltip = f'You can hide {project.name} from your list.'
        icon = 'bi bi-eye-slash'
    return format_html(f"""
<a href="#" id="project-showhide-{project.id}" role="button" class="btn btn-secondary btn-sm"><span class="{icon}" aria-hidden="true" data-toggle="{tooltip}" title="" data-placement="top"></span></a>
    """)


@register.simple_tag
def button_project_delete(project):
    link = reverse('project:delete', args = [ project.id ])
    return format_html(f"""
<a href="{link}" role="button" class="btn btn-danger btn-sm" onclick="return confirm('Are you sure?');"><span class="oi oi-trash" aria-hidden="true" data-toggle="tooltip" title="Delete project {project.name}." data-placement="top"></span></a>
    """)


@register.simple_tag
def number_square(icon, x):
    #return format_html(f"""<span class="badge bg-secondary" >{x}</span>""") if x else ""
    return format_html(f"""
<i class="{icon} position-relative" data-bs-toggle="tooltip" title="The number of hidden projects">
  <span class="position-absolute top-0 start-100 translate-middle badge bg-secondary small">
    {x}
  </span>
</i>
    """) if x else format_html(f"""
<i class="{icon}"></i>
    """)

