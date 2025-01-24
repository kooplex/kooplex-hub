from django import template
from django.utils.html import format_html
from django.urls import reverse
from django.template.defaultfilters import truncatechars

from hub.templatetags.extras import render_user
from ..models import Project

register = template.Library()

pid = lambda project: project.id if project else ""


@register.simple_tag
def button_fetch_joinable_projects(user):
    return format_html(f"""
<button type="button" class="btn btn-secondary btn-sm rounded rounded-5 border border-2 border-dark mb-2" data-bs-toggle="modal" data-bs-target="#joinprojectModal" data-id="{user.id}">
    <i class="bi bi-boxes pe-1"></i>
    Retrieve joinable projects...
</button>
    """)


@register.simple_tag
def button_new_project(user):
    return format_html(f"""
<button type="button" class="btn btn-secondary btn-sm rounded rounded-5 border border-2 border-dark mb-2" data-bs-toggle="modal" data-bs-target="#newProjectModal" data-id="{user.id}">
    <i class="bi bi-plus-square pe-1"></i>
    Create new project...
</button>
    """)


@register.simple_tag
def project_card_border(project = None):
    return "border-success" if project else "border-warning"


#@register.simple_tag
#def project_folder(project = None):
#    editable = "" if project else "editable"
#    folder = project.subpath if project else "Add a folder"
#    return format_html(f"""
#<p class="card-text mb-1"><strong>Folder:</strong>
#<span data-type="text" data-title="Define project folder" data-pk="{pid(project)}" data-field="subpath" data-typed="false"
#   class="{editable} fw-bold w-100 text-dark text-start" data-placement="right">{folder}</span>
#</p>
#    """)


@register.simple_tag
def project_creator(project = None, user = None):
    return format_html(f"""
<p class="card-text mb-2"><strong>Creator:</strong> {project.creator.profile.name_and_username}</p>
    """) if project and project.creator != user else ""


@register.simple_tag
def project_scope(project = None):
    return format_html(f"""
<div id="project-scope-{pid(project)}">
    <button class="badge rounded-pill border border-2 border-dark p-3 ms-2 text-dark position-relative" name="{Project.SCP_PRIVATE}"
            data-toggle="tooltip" title="Make project public"
            onclick="projectScopeButtonClick('{pid(project)}', '{Project.SCP_PUBLIC}')">
      <i class="oi oi-key"></i>
      <span class="position-absolute top-0 start-100 translate-middle badge bg-success small">private</span>
    </button>
    <button class="badge rounded-pill border border-2 border-dark p-3 ms-2 text-dark position-relative" name="{Project.SCP_PUBLIC}"
            data-toggle="tooltip" title="Make project private"
            onclick="projectScopeButtonClick('{pid(project)}', '{Project.SCP_PRIVATE}')">
      <i class="oi oi-cloud"></i>
      <span class="position-absolute top-0 start-100 translate-middle badge bg-success small">puplic</span>
    </button>
</div>
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
def list_reports(project = None):
    reps = project.reports if project else []
    t = "<br>".join([ render_report(r) for r in reps ])
    return format_html(f"""
<p class="card-text mb-0"><strong>Reports:</strong></p>
<p class="card-text">{t}</p>
    """) if reps else ""


@register.filter
def link_project_drop(project):
    return reverse('project:delete', args = [ pid(project) ]) if project else ""


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


#FIXME CONFLICT
@register.simple_tag
def button_save_project_changes(project = None):
    return format_html(f"""
<span id="project-save-{pid(project)}" class="badge rounded-pill bg-danger text-light p-3 me-3 d-none" role="button"
      onclick="save_project_config('{pid(project)}')">
  <i class="bi bi-save me-1"></i><span>Save changes</span>
</span>
    """)


