from django import template
from django.utils.html import format_html
from django.urls import reverse

from ..models import Container
from volume.models import Volume
from container.lib.cluster_resources_api import *
import pandas

from django.template.defaultfilters import truncatechars

register = template.Library()

@register.simple_tag
def container_name(container):
    cn = truncatechars(container.name, 45)
    return format_html(f"""<h5 id="container-name-{container.id}" style="display: inline" class="card-title fw-bold">{cn}</h5>""")

@register.simple_tag
def ifempty(container):
    if container.projects or container.courses or hasattr(container, "report"):
        return ""
    return format_html(f"""
<span id="container-empty-{container.id} class="badge rounded-pill bg-warning " data-bs-toggle="tooltip" 
      title="This environment is not bound to any projects, courses or reports yet"
      data-placement="bottom"><i class="oi oi-warning"></i>empty</span>
    """)

@register.simple_tag
def container_image(container_or_image):
    container = container_or_image if isinstance(container_or_image, Container) else Container(image = container_or_image)
    i = container.image.name.split('/')[-1]
    if container.state == container.ST_NEED_RESTART:
        bg = 'bg-danger'
        tooltip = f'Environment {container.name} needs restart'
    elif container.state == container.ST_RUNNING:
        bg = 'bg-success'
        tooltip = f'Environment {container.name} is running fine'
    elif container.state in [ container.ST_STOPPING, container.ST_STARTING ]:
        bg = 'bg-warning'
        tooltip = f'Environment {container.name} is changing phase...'
    else:
        bg = 'bg-secondary'
        tooltip = ''
    w_id = f'id="container-image-{container.id}"' if container.id else ''
    return format_html(f"""
<span {w_id} class="badge rounded-pill {bg} p-2" 
      data-bs-toggle="tooltip" data-placement="bottom" 
      title="{tooltip} "><i class="ri-image-2-line"></i>&nbsp; {i}</span>
    """)


@register.simple_tag
def container_state(container):
    state = container.check_state()
    msg = state.get('message', 'No extra information returned').replace('{', '(').replace('}', ')')
    state_ = container.get_state_display()
    phase = state.get('phase', 'Missing')
    #FIXME: rename id: containerstate- container-state-
    return format_html(f"""
<span id="containerstate-{container.id}" class="badge rounded-pill p-2 bg-dark text-light"
      data-bs-toggle="tooltip" data-placement="bottom" 
      title="Kubernetes message: {msg}">
  {phase}&nbsp;/&nbsp;{state_}
</span>
    """)


@register.simple_tag
def container_resources(container):
    cn = container.name
    # query actual resource usage of container
    label = container.label
    usage = pandas.DataFrame(get_pod_usage(container_name=label))
    if usage.shape[0]>1:
        #FIXME raise
        used_cpu = -1
        used_memory = -1
        used_gpu = -1
    elif usage.shape[0]==1:
        used_cpu = usage["used_cpu"][0]
        used_memory = usage["used_memory"][0]
        used_gpu = usage["used_gpu"][0]
    else:
        used_cpu = "-"
        used_memory = "-"
        used_gpu = "-"

    gpu = f"""
<span class="badge rounded-pill bg-warning text-dark p-2" 
      data-bs-toggle="tooltip" data-placement="bottom" 
      title="The number of GPU devices requested for environment {cn}"><i class="bi bi-gpu-card"></i>&nbsp;{used_gpu}/{container.gpurequest}</span>
    """ if container.gpurequest else ""
    node = f"""
<span class="badge rounded-pill bg-warning text-dark p-2" 
      data-bs-toggle="tooltip" data-placement="bottom" 
      title="Your environment {cn} is assigned to compute node {container.node}"><i class="bi bi-pc"></i>&nbsp;{container.node}</span>
    """ if container.node else ""
    return format_html(f"""
<div id="container-resources-{container.id}" style="display: inline">
  {node}
  <span class="badge rounded-pill bg-warning text-dark p-2" 
        data-bs-toggle="tooltip" data-placement="bottom" 
        title="The CPU clock cycles requested for environment {cn}"><i class="bi bi-cpu"></i>&nbsp;{used_cpu}/{container.cpurequest}</span>
  {gpu}
  <span class="badge rounded-pill bg-warning text-dark p-2" 
        data-bs-toggle="tooltip" data-placement="bottom" 
        title="The requested memory for environment {cn}"><i class="bi bi-memory"></i>&nbsp;{used_memory}/{container.memoryrequest}&nbsp;GB</span>
  <span class="badge rounded-pill bg-warning text-dark p-2" 
        data-bs-toggle="tooltip" data-placement="bottom" 
        title="The maximum allowed idle time for environment {cn}"><i class="bi bi-clock-history"></i>&nbsp;{container.idletime}&nbsp;h</span>
</div>
    """)


@register.simple_tag
def container_mounts(container):
    p = container.projects
    P = "\n".join(map(lambda x: f"{x.name} {x.description}", p))
    c = container.courses
    C = "\n".join(map(lambda x: f"{x.name} {x.description}", c))
    v = container.volumes
    vt = lambda x: 'a' if x.scope == Volume.SCP_ATTACHMENT else 'v'
    V = "\n".join(map(lambda x: f"{x.folder} ({vt(x)}): {x.description}", v))
    vis = lambda x: '' if len(x) else 'd-none'
    return format_html(f"""
<div id="container-mounts-{container.id}" style="display: inline">
  <span class="badge rounded-pill bg-dark {vis(p)}" aria-hidden="true" data-bs-toggle="tooltip" title="Projects:\n{P}" data-placement="top"><i class="ri-product-hunt-line"></i> {len(p)}</span>
  <span class="badge rounded-pill bg-dark {vis(c)}" aria-hidden="true" data-bs-toggle="tooltip" title="Courses:\n{C}" data-placement="top"><i class="ri-copyright-line"></i> {len(c)}</span>
  <span class="badge rounded-pill bg-dark {vis(v)}" aria-hidden="true" data-bs-toggle="tooltip" title="Volumes/Attachments:\n{V}" data-placement="top"><i class="ri-database-2-line"></i> {len(v)}</span>
</div>
    """)
#	  {% report container.report %} {# FIXME: handle report and other images in the same list #}
#	  {% synchfolders container %}  {# FIXME: check implementation when seafile integrated #}
#	  {% repos container %}         {# FIXME: check implementation when gitea integrated #}


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
<span class="bg-warning p-2"><span class="bi bi-exclamation-triangle">&nbsp;<strong aria-hidden="true" data-toggle="tooltip" title="{container.restart_reasons}">Needs restart</strong></span></span>
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
def button_start_open(container, id_suffix = ''):
    if container.state in [ container.ST_RUNNING, container.ST_NEED_RESTART ]:
        tooltip = f'Jump to environment {container.name}'
        icon_class = 'oi oi-external-link'
        extra = ''
        link = reverse('container:open', args = [container.id])
        hidden = f"""
<input type="hidden" id="url-containeropen-{container.id}{id_suffix}" value="{link}">
<input type="hidden" name="target" value="open">
        """
    elif container.state == container.ST_NOTPRESENT:
        tooltip = f'Start environment {container.name}'
        icon_class = 'bi bi-lightning'
        extra = ''
        hidden = '<input type="hidden" name="target" value="start">'
    else:
        tooltip = f'unhandled {container.name} {container.state}'
        icon_class = 'spinner-grow spinner-grow-sm'
        extra = 'role="status"'
        hidden = ''
    return format_html(f"""
<button id="container-startopen-{container.id}{id_suffix}"
        class="btn btn-success btn-sm " 
        data-toggle="tooltip" title="{tooltip}"
        onclick="handle_click(this)"
>
  <span class="{icon_class}" aria-hidden="true" {extra}></span>
  {hidden}
</button>
    """)

#@register.simple_tag
#def button_report_start(container):
#    link = reverse('container:report_open', args = [container.id])
#    return format_html(f"""
#<button name="container-report-open" value="{container.id}"
#        class="btn btn-success btn-sm " 
#        data-toggle="tooltip" title="Open report url {container.name}"
#>
#  <span id="container-report-open-{container.id}" class="oi oi-external-link {s}" aria-hidden="true"></span>
#  <input type="hidden" id="url-containerreportopen-{container.id}" value="{link}">
#</button>
#    """)

@register.simple_tag
def button_stop(container):
    if container.state in [ container.ST_RUNNING, container.ST_NEED_RESTART ]:
        tooltip = f'Stop environment {container.name}'
        icon_class = 'bi bi-x-lg'
        extra = ''
        butt_extra = ''
    elif container.state == container.ST_NOTPRESENT:
        tooltip = f''
        icon_class = 'bi bi-x-lg'
        extra = ''
        butt_extra = 'disabled'
    else:
        kubestate = container.check_state()
        phase = kubestate.get('phase', None)
        butt_extra = ''
        if phase == 'Pending':
            tooltip = f'Environment {container.name} is in a pending state...'
            icon_class = 'bi bi-x-lg'
            extra = ''
        else:
            tooltip = f'Unhandles situation {container.name} state: {container.state} phase: {phase}'
            icon_class = 'spinner-grow spinner-grow-sm'
            extra = 'role="status"'
    return format_html(f"""
<button id="container-stop-{container.id}"
        class="btn btn-danger btn-sm " 
        data-toggle="tooltip" title="{tooltip}"
        onclick="handle_click(this)" {butt_extra}
>
  <span class="{icon_class}" aria-hidden="true" {extra}></span>
  <input type="hidden" name="target" value="stop">
</button>
    """)


@register.simple_tag
def button_restart(container):
    if container.state in [ container.ST_RUNNING, container.ST_NEED_RESTART ]:
        icon_class = 'bi bi-bootstrap-reboot'
        butt_extra = ''
        extra = ''
    elif container.state == container.ST_NOTPRESENT:
        icon_class = 'bi bi-bootstrap-reboot'
        extra = ''
        butt_extra = 'disabled'
    else:
        icon_class = 'spinner-grow spinner-grow-sm'
        extra = 'role="status"'
        butt_extra = ''

    return format_html(f"""
<button id="container-restart-{container.id}"
        class="btn btn-warning btn-sm" 
        data-toggle="tooltip" title="Restart inconsistent environment {container.name}"
        onclick="handle_click(this)" {butt_extra}
>
  <span class="{icon_class}" aria-hidden="true" {extra}></span>
  <input type="hidden" name="target" value="restart">
</button>
    """)




@register.simple_tag
def button_refreshlog(container, modal_prefix = None):
    if modal_prefix:
        return format_html(f"""
<button class="btn btn-warning btn-sm mb-1" 
        data-bs-toggle="modal" data-bs-target="#{modal_prefix}{container.id}"
        ><span class="bi bi-patch-question" aria-hidden="true" 
               data-toggle="tooltip" title="Click to retrieve latest container logs" data-placement="bottom"></span></button>
        """)
    return format_html(f"""
<button name="container-log" value="{container.id}" class="btn btn-warning btn-sm mb-1" 
        data-toggle="tooltip" title="Click to retrieve latest container logs" data-placement="bottom" disabled>
        <span id="container-log-{container.id}" class="bi bi-patch-question d-none" aria-hidden="true"></span>
        <span id="spinner-log-{container.id}" class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
</button>
    """)


@register.simple_tag
def button_configure(container):
    #link = reverse('container:configure', args = [container.id])
    return format_html(f"""
<a href="#" onClick="configure({container.id})" role="button" class="btn btn-warning btn-sm"><span class="bi bi-tools" aria-hidden="true" data-toggle="tooltip" title="Add/remove project to the service" data-placement="bottom"></span></a>
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


#FIXME
#<a href="{link}" role="button" class="btn btn-secondary btn-sm" value="{b.container.id}"><span class="bi bi-boxes" aria-hidden="true"></span>{b.container.name}</a>
# Attribute value not allowed on element a
@register.simple_tag
def dropdown_start_open(bindings, ancestor, ancestor_type, id_suffix = ''):
    if len(bindings):
        items = ""
        for b in bindings:
            but_start_open = button_start_open(b.container, id_suffix)
            link = reverse('container:list')
            items += f"""
<div class="dropdown-item" style="display: inline-block">
  <div class="btn-group" role="group" aria-label="control buttons">
    {but_start_open}
    <a href="{link}" role="button" class="btn btn-secondary btn-sm" value="{b.container.id}"><span class="bi bi-boxes" aria-hidden="true"></span>{b.container.name}</a>
  </div>
</div>
            """
        an = getattr(ancestor, ancestor_type).name
        return format_html(f"""
<div class="dropdown" style="display: inline-block" data-bs-toggle="tooltip" data-bs-placement="top" title="Service environments associated with {ancestor_type} {an}">
  <button class="btn btn-outline-secondary dropdown-toggle btn-sm" id="dc-svcs-{ancestor.id}" data-bs-toggle="dropdown" aria-expanded="false">
    <i class="oi oi-terminal"></i>&nbsp;{len(bindings)}
  </button>
  <div class="dropdown-menu" aria-labelledby="dc-svcs-{ancestor.id}">
    {items}
  </div>
</div>
        """)
    else:
        if ancestor_type == 'project':
            link = reverse('project:autoaddcontainer', args = [ancestor.id])
        elif ancestor_type == 'course':
            link = reverse('education:autoaddcontainer', args = [ancestor.id])
        else:
            link = '#'
        return format_html(f"""
<a class="btn btn-danger btn-sm" role="button" href="{link}">
  <i class="bi bi-boxes" data-bs-toggle="tooltip" data-bs-placement="top" title="Create a default environment for your {ancestor_type}"></i>
</a>
        """)


