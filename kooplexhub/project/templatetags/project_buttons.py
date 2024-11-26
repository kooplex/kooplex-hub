from django import template
from django.utils.html import format_html
from django.urls import reverse
from django.template.defaultfilters import truncatechars

from hub.templatetags.extras import render_user
from ..models import Project

register = template.Library()

pid = lambda project: project.id if project else "new"


@register.simple_tag
def project_card_border(project = None):
    return "border-secondary" if project else "border-danger"


@register.simple_tag
def project_name(project = None):
    pn = project.name if project else "Add a name"
    return format_html(f"""
<div data-type="text" data-title="Edit project name" data-pk="{pid(project)}" data-field="name" data-orig="{pn}" 
   class="editable fw-bold badge rounded-pill p-3 text-dark border border-2 border-dark text-start flex-grow-1" data-placement="right">{truncatechars(pn, 45)}</div>
    """)


@register.simple_tag
def project_folder(project = None):
    editable = "" if project else "editable"
    folder = project.subpath if project else "Add a folder"
    return format_html(f"""
<p class="card-text mb-1"><strong>Folder:</strong>
<span data-type="text" data-title="Define project folder" data-pk="{pid(project)}" data-field="subpath" data-typed="false"
   class="{editable} fw-bold w-100 text-dark text-start" data-placement="right">{folder}</span>
</p>
    """)


@register.simple_tag
def project_image(project = None):
    if project and project.preferred_image:
        iid = project.preferred_image.id
        ihn = truncatechars(project.preferred_image.hr, 20)
    else:
        iid = -1
        ihn = "Select image..."
    return format_html(f"""
<button data-pk="{pid(project)}" data-field="image" data-orig="{iid}" 
      class="badge rounded-pill p-3 border border-2 border-dark flex-grow-1 text-start text-dark" 
      onclick="ImageSelection.openModal('{pid(project)}', {iid}, 'preferred_image')" role="button">
  <i class="ri-image-2-line me-2"></i><span name="name" data-pk="{pid(project)}">{ihn}</span>
</button>
    """)


@register.simple_tag
def project_description(project = None):
    d = project.description if project else "Add a description"
    return format_html(f"""
<div role="button">
    <p class="card-text mb-1"><strong>Description:</strong></p>
    <p class="card-text editable"
       data-type="textarea" data-pk="{pid(project)}" data-title="Edit Description"
       data-name="description" data-placement="right" data-field="description" data-orig="{d}"
    >{d}</p>
</div>
    """)


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
def list_collaborators(project = None, user = None):
    upbs = project.userprojectbindings if project else []
    t = "<br>".join([ render_user(upb.user) for upb in upbs if upb.user != user ]) if upbs else "click to add"
    u = [ upb.user.id for upb in upbs if upb.user != user ]
    a = [ upb.user.id for upb in upbs if upb.user != user and upb.role == upb.RL_ADMIN ]
    return format_html(f"""
<div onclick="UserSelection.openModal('{pid(project)}')" role="button" class="content" 
    data-pk="{pid(project)}" data-userlist="{u}" data-adminlist="{a}">
    <p class="card-text mb-1"><strong>Collaborators:</strong></p>
    <p class="card-text my-0">{t}</p>
</div>
    """)


@register.simple_tag
def list_volumes(project = None):
    from volume.templatetags.volume_buttons import render_volume
    vols = project.volumes if project else []
    t = "<br>".join([ render_volume(v) for v in vols ]) if vols else "click to add"
    v = [ v.id for v in vols ]
    return format_html(f"""
<div onclick="VolumeSelection.openModal('{pid(project)}')" role="button" class="content" 
    data-pk="{pid(project)}" data-volumes="{v}">
    <p class="card-text mb-1"><strong>Volumes:</strong></p>
    <p class="card-text my-0">{t}</p>
</div>
    """)


@register.simple_tag
def list_reports(project = None):
    reps = project.reports if project else []
    t = "<br>".join([ render_report(r) for r in reps ])
    return format_html(f"""
<p class="card-text mb-0"><strong>Reports:</strong></p>
<p class="card-text">{t}</p>
    """) if reps else ""


@register.simple_tag
def button_project_delete(project = None):
    if project:
        link = reverse('project:delete', args = [ pid(project) ])
        return format_html(f"""
<a href="{link}" role="button" class="badge rounded-pill text-bg-danger border text-light p-3" onclick="return confirm('Are you sure?');"><span class="oi oi-trash" aria-hidden="true" data-toggle="tooltip" title="Delete project {project.name}." data-placement="top"></span></a>
        """)
    else:
        return ""


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


