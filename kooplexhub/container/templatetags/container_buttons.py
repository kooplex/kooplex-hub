from django import template
from django.utils.html import format_html
from django.urls import reverse

from ..models import Container

register = template.Library()

@register.simple_tag
def ifempty(container):
    if container.projects or container.courses or hasattr(container, "report"):
        return ""
    return format_html("""
<span class="badge rounded-pill bg-warning " data-bs-toggle="tooltip" 
      title="This environment is not bound to any projects, courses or reports yet"
      data-placement="bottom"><i class="oi oi-warning"></i>empty</span>
    """)

@register.simple_tag
def container_image(container_or_image):
    container = container_or_image if isinstance(container_or_image, Container) else Container(image = container_or_image)
    i = container.image.name.split('/')[-1]
    if container.state == container.ST_NEED_RESTART:
        return format_html(f"""
<span class="badge rounded-pill bg-danger text-light" 
      data-bs-toggle="tooltip" data-placement="bottom" 
      title="Environment {container.friendly_name} needs restart"><i class="ri-image-2-line"></i>&nbsp; {i}</span>
        """)
    elif container.state == container.ST_RUNNING:
        return format_html(f"""
<span class="badge rounded-pill bg-success" 
      data-bs-toggle="tooltip" data-placement="bottom" 
      title="Environment {container.friendly_name} is running fine"><i class="ri-image-2-line"></i>&nbsp; {i}</span>
        """)
    else:
        return format_html(f"""<span class="badge rounded-pill bg-secondary "><i class="ri-image-2-line"></i>&nbsp; {i}</span>""")


@register.simple_tag
def volumes(*args, **kwargs):
    v = kwargs.get('volumes', [])
    V = "\n".join(map(lambda x: f"{x.name}: {x.description}", v))
    return format_html(f"""
<span class="badge rounded-pill bg-dark" aria-hidden="true" data-bs-toggle="tooltip" title="Volumes:\n{V}" data-placement="top"><i class="ri-database-2-line"></i> {len(v)}</span>
    """) if len(v) else ""


@register.simple_tag
def attachments(*args, **kwargs):
    a = kwargs.get('attachments', [])
    A = "\n".join(map(lambda x: f"{x.name} {x.description}", a))
    return format_html(f"""
<span class="badge rounded-pill bg-dark" aria-hidden="true" data-bs-toggle="tooltip" title="Attachments:\n{A}" data-placement="top"><i class="ri-attachment-2"></i> {len(a)}</span>
    """) if len(a) else ""


@register.simple_tag
def projects(*args, **kwargs):
    p = kwargs.get('projects', [])
    P = "\n".join(map(lambda x: f"{x.name} {x.description}", p))
    return format_html(f"""
<span class="badge rounded-pill bg-dark" aria-hidden="true" data-bs-toggle="tooltip" title="Projects:\n{P}" data-placement="top"><i class="ri-product-hunt-line"></i> {len(p)}</span>
    """) if len(p) else ""


@register.simple_tag
def courses(*args, **kwargs):
    c = kwargs.get('courses', [])
    C = "\n".join(map(lambda x: f"{x.name} {x.description}", c))
    return format_html(f"""
<span class="badge rounded-pill bg-dark" aria-hidden="true" data-bs-toggle="tooltip" title="Courses:\n{C}" data-placement="top"><i class="ri-copyright-line"></i> {len(c)}</span>
    """) if len(c) else ""


@register.simple_tag
def report(report):
    return format_html(f"""
<span class="badge rounded-pill bg-secondary" aria-hidden="true" data-bs-toggle="tooltip" 
      title="Report service environment for {report.name}"
      data-placement="top"><i class="oi oi-graph"></i> {report.name}</span>
        """) if report else ""


@register.simple_tag
def synchfolders(container):
    return ""
#FIXME:
#          {% if container.synced_libraries|length > 0 %}
#            <span class="badge rounded-pill bg-dark" aria-hidden="true" data-bs-toggle="tooltip" title="Synchron folders:
#{% for l in container.synced_libraries %}
#{{ l.library_name }} from server {{ l.token.syncserver.url }}
#{% endfor %}" data-placement="top"><i class="ri-refresh-fill"></i> {{container.synced_libraries|length}}</span>
#          {% endif %}


@register.simple_tag
def repos(container):
    return ""
#FIXME:
#          {% if container.repos|length > 0 %}
#            <span class="badge rounded-pill bg-dark" aria-hidden="true" data-bs-toggle="tooltip" title="Version control repositories:
#{% for r in container.repos %}
#{{ r.project_name }} from server {{ r.token.repository.url }}
#{% endfor %}" data-placement="top"><i class="ri-git-repository-line"></i> {{container.repos|length}}</span>
#          {% endif %}


@register.simple_tag
def container_restart_reason(container):
    return format_html(f"""
<p class="card-text">
  <div class="alert alert-warning" style="height: 120px" role="alert">
    <strong>Needs restart:</strong> {container.restart_reasons}
  </div>
</p>
    """) if container.restart_reasons else ""


@register.simple_tag
def button_delete_container(container):
    if hasattr(container, "report"):
        return ""
    link = reverse('container:destroy', args = [container.id])
    msg = f"Are you sure you want to drop your container {container}?"
    return format_html(f"""
<div class="float-end">
  <a href="{link}" onclick="return confirm('{msg}');" role="button" class="btn btn-danger btn-sm"><span class="oi oi-trash" aria-hidden="true" data-toggle="tooltip" title="Remove {container.name}"></span></a>
</div>
    """)


@register.simple_tag
def button_start_open(container):
    o, s = ('d-none', '') if container.state in [ container.ST_RUNNING, container.ST_NEED_RESTART ] else ('', 'd-none')
    link = reverse('container:open', args = [container.id])
    return format_html(f"""
<button name="container-start" value="{container.id}" role="button" 
        class="btn btn-success btn-sm " 
        data-toggle="tooltip" title="Start environment {container.name}"
>
  <span id="container-start-{container.id}" class="bi bi-lightning {o}" aria-hidden="true"></span>
  <span id="container-open-{container.id}" class="oi oi-external-link {s}" aria-hidden="true"></span>
  <span id="spinner-start-{container.id}" class="spinner-grow spinner-grow-sm d-none" role="status" aria-hidden="true"></span>
  <input type="hidden" id="url-containeropen-{container.id}" value="{link}">
</button>
    """)


@register.simple_tag
def button_stop(container):
    return format_html(f"""
<button name="container-stop" value="{container.id}" role="button" 
        class="btn btn-danger btn-sm " 
        data-toggle="tooltip" title="Stop environment {container.name}"
>
  <span id="container-stop-{container.id}" class="bi bi-x-lg" aria-hidden="true"></span>
  <span id="spinner-stop-{container.id}" class="spinner-grow spinner-grow-sm d-none" role="status" aria-hidden="true"></span>
</button>
    """)


@register.simple_tag
def button_restart(container):
    return format_html(f"""
<button name="container-restart" value="{container.id}" role="button" 
        class="btn btn-warning btn-sm" 
        data-toggle="tooltip" title="Restart inconsistent environment {container.name}"
>
  <span id="container-restart-{container.id}" class="bi bi-bootstrap-reboot" aria-hidden="true"></span>
  <span id="spinner-restart-{container.id}" class="spinner-grow spinner-grow-sm d-none" role="status" aria-hidden="true"></span>
</button>
    """)




@register.simple_tag
def button_refreshlog(container, modal_prefix = None):
    if modal_prefix:
        return format_html(f"""
<button role="button" class="btn btn-warning btn-sm mb-1" 
        data-bs-toggle="modal" data-bs-target="#{modal_prefix}{container.id}"
        ><span class="bi bi-patch-question" aria-hidden="true" 
               data-toggle="tooltip" title="Click to retrieve latest container logs" data-placement="bottom"></span></button>
        """)
    return format_html(f"""
<button name="container-log" value="{container.id}" role="button" class="btn btn-warning btn-sm mb-1" 
        data-toggle="tooltip" title="Click to retrieve latest container logs" data-placement="bottom" disabled>
        <span id="container-log-{container.id}" class="bi bi-patch-question d-none" aria-hidden="true"></span>
        <span id="spinner-log-{container.id}" class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
</button>
    """)


@register.simple_tag
def button_configure(container):
    link = reverse('container:configure', args = [container.id])
    return format_html(f"""
<a href="{link}" role="button" class="btn btn-warning btn-sm"><span class="bi bi-tools" aria-hidden="true" data-toggle="tooltip" title="Add/remove project to the service" data-placement="bottom"></span></a>
    """)


@register.simple_tag
def button_configure_attachment(attachment, user):
    if attachment.creator == user:
        link = reverse('container:configure_attachment', args = [attachment.id])
        return format_html(f"""
<a href="{link}" role="button" class="btn btn-secondary btn-sm"><span class="oi oi-wrench" aria-hidden="true" data-toggle="tooltip" title="Update the name or description of this attachment" data-placement="bottom"></span></a>
        """)
    else:
        return ""


@register.simple_tag
def dropdown_start_open(bindings, ancestor, ancestor_type):
    if len(bindings):
        items = ""
        for b in bindings:
            but_start_open = button_start_open(b.container)
            but_stop = button_stop(b.container)
            items += f"""
  <span class="dropdown-item">
    <div class="btn-group" role="group" aria-label="control buttons">
      <span>
        {but_start_open}
        {but_stop}
        {b.container.name}
      </span>
  </div>
    </span>
            """
        an = getattr(ancestor, ancestor_type).name
        return format_html(f"""
<span class="dropdown" data-bs-toggle="tooltip" data-bs-placement="top" title="Service environments associated with {ancestor_type} {an}">
  <a class="btn btn-outline-secondary dropdown-toggle btn-sm" type="button" id="dc-svcs-{ancestor.id}" data-bs-toggle="dropdown" aria-expanded="false">
    <i class="oi oi-terminal"></i>&nbsp;{len(bindings)}
  </a>
  <ul class="dropdown-menu" aria-labelledby="dc-svcs-{ancestor.id}">
    {items}
  </ul>
</span>
        """)
    else:
        if ancestor_type == 'project':
            link = '#'
        elif ancestor_type == 'course':
            link = reverse('education:autoaddcontainer', args = [ancestor.id])
        else:
            link = '#'
        return format_html(f"""
<a class="btn btn-danger btn-sm" type="button" href="{link}">
  <i class="bi bi-boxes" data-bs-toggle="tooltip" data-bs-placement="top" title="Create a default environment for your {ancestor_type}"></i>
</a>
        """)


