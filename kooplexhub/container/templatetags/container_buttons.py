from django import template
from django.utils.html import format_html
from django.urls import reverse

from ..models import Container
from volume.models import Volume
from container.lib.cluster_resources_api import *
import pandas

from django.template.defaultfilters import truncatechars

register = template.Library()

visible = lambda x: "" if x else "d-none"
cid = lambda container: container.id if container else "new"


@register.simple_tag
def card_border(container = None):
    if container:
        # conditional formatting
        #if container.image.imagetype == container.image.TP_PROJECT:
        #if container.image.imagetype == container.image.TP_REPORT:
        #if container.image.imagetype == container.image.TP_API:
        # lehet hátteret is betehetjük majd
        return "border-warning"
    else:
        return "border-danger"


@register.simple_tag
def container_name(container = None):
    cn = truncatechars(container.name, 45) if container else "Add a name"
    return format_html(f"""
<a href="#" data-type="text" data-title="Edit container name" data-pk="{cid(container)}" data-field="name" data-orig="{cn}" 
   class="editable fw-bold mx-2 badge rounded-pill w-100 p-2 text-dark border border-2 border-dark text-start" data-placement="right">{cn}</a>
    """)


@register.simple_tag
def button_new_container():
    return format_html(f"""
<button class="badge rounded-pill text-bg-success border p-2" name="new"
        data-toggle="tooltip" title="Create a new environment based on the settings" disabled>
    <span class="bi bi-plus-lg"></span>
</button>
    """)


@register.simple_tag
def button_teleport(container = None):
    return format_html(f"""
<div id="container-teleport-{cid(container)}">
    <button class="badge rounded-pill text-bg-success border p-3 me-2" name="grant"
            data-toggle="tooltip" title="Grant remote access"
            onclick="teleportButtonClick('{cid(container)}', true)">
      <span class="bi bi-door-closed" aria-hidden="true" role="status"></span>
    </button>
    <button class="badge rounded-pill text-bg-warning border p-3 me-2" name="revoke"
            data-toggle="tooltip" title="Revoke remote access"
            onclick="teleportButtonClick('{cid(container)}', false)">
      <span class="bi bi-door-open" aria-hidden="true"></span>
    </button>
</div>
    """)


@register.simple_tag
def container_image(container = None):
    if container:
        iid = container.image.id
        ihn = container.image.hr
    else:
        iid = -1
        ihn = "Select image..."
    return format_html(f"""
<span data-pk="{cid(container)}" data-field="image" data-orig="{iid}" 
      class="badge rounded-pill text-bg-secondary p-3 border border-2 border-dark flex-grow-1 text-start" 
      onclick="ImageSelection.openModal('{cid(container)}', {iid})" role="button">
  <i class="ri-image-2-line me-2"></i><span name="name" data-pk="{cid(container)}">{ihn}</span>
</span>
    """)


@register.simple_tag
def container_state(container = None):
    state = container.check_state() if container else {}
    phase = state.get('phase', 'Missing')
    return format_html(f"""
<span data-pk="{cid(container)}" name="phase" class="badge rounded-pill bg-dark text-light p-3 flex-grow-1 text-start">{phase}</span>
    """) if container else ""


@register.simple_tag
def container_resources(container = None):
    _atlist = [ "node", "cpurequest", "gpurequest", "memoryrequest", "idletime"]
    geta = lambda container, attr: getattr(container, attr, None) if container else None
    atts = { a: geta(container, a) for a in _atlist }
    cn = container.name if container else ""
    hv = { a: "" if v else "d-none" for a, v in atts.items() }
    empty = "d-none" if len(_atlist)>list(atts.values()).count(None) else ""
    return format_html(f"""
<div id="container-resources-{cid(container)}" style="display: inline"
      data-bs-toggle="tooltip" data-placement="bottom"
      title="Requested compute resources. Double click to tune."
      onclick="ComputeResourceSelection.openModal('{cid(container)}', \'{atts['node']}\')">
  <span class="badge rounded-pill bg-warning text-dark p-3 border border-2 border-dark w-100 text-start" role="button">
    <span class="{hv['node']}" name="node"><i class="bi bi-pc me-1"></i><span name="node_name" class="me-2">{atts['node']}</span></span>
    <span class="{hv['cpurequest']}" name"cpu"><i class="bi bi-cpu me-1"></i><span name="node_cpu_request" class="me-2">{atts['cpurequest']}</span></span>
    <span class="{hv['gpurequest']}" name="gpu"><i class="bi bi-gpu-card me-1"></i><span name="node_gpu_request" class="me-2">{atts['gpurequest']}</span></span>
    <span class="{hv['memoryrequest']}" name="mem"><i class="bi bi-memory me-1"></i><span name="node_mem_request" class="me-2">{atts['memoryrequest']} GB</span></span>
    <span class="{hv['idletime']}" name="up"><i class="bi bi-clock-history me-1"></i><span name="node_idle" class="me-2">{atts['idletime']} h</span></span>
    <span class="{empty}" name="empty"><i class="bi bi-wrench-adjustable me-1"></i>default resources</span>
  </span>
</div>
    """)


#FIXME: az aktuális fogyasztás mehet a loglekérésbe vagy háttészínbe
#@register.simple_tag
#def container_resources(container = None):
#        # query actual resource usage of container
#        usage = pandas.DataFrame(get_pod_usage(container_name=container.label))
#        if usage.shape[0]==1:
#            used_cpu = usage["used_cpu"][0]
#            used_memory = usage["used_memory"][0]
#            used_gpu = usage["used_gpu"][0]


@register.simple_tag
def container_mounts(container = None):
    hs = lambda x: "" if x else "d-none"
    if container:
        p = len(container.projects)
        c = len(container.courses)
        v = len(container.volumes)
    else:
        p=v=c=0
    empty = "d-none" if p+v+c else ""
    return format_html(f"""
<div id="container-mounts-{cid(container)}" style="display: inline"
      data-bs-toggle="tooltip" data-placement="bottom"
      title="Requested filesystem resources. Double click to change mounts."
      onclick="FileResourceSelection.openModal('{cid(container)}')">
  <span class="badge rounded-pill bg-secondary-subtle p-3 border border-2 border-secondary text-dark w-100 text-start">
    <span class="{hs(p)}" name="project"><i class="ri-product-hunt-line me-1"></i><span name="project_count" class="me-2">{p}</span></span>
    <span class="{hs(c)}" name="course"><i class="ri-copyright-line me-1"></i><span name="course_count" class="me-2">{c}</span></span>
    <span class="{hs(v)}" name="volume"><i class="ri-database-2-line me-1"></i><span name="volume_count" class="me-2">{v}</span></span>
    <span class="{empty}" name="empty"><i class="bi bi-folder me-2"></i>default mounts</span>
  </span>
</div>
    """)


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


@register.simple_tag
def repos(container):
    return ""


@register.simple_tag
def container_restart_reason(container = None):
    return format_html(f"""
<span id="container-restartreason-{container.id}" class="{visible(container.restart_reasons)} badge rounded-pill text-bg-warning border p-3 border border-2 border-danger w-100"
      data-toggle="tooltip" title="{container.restart_reasons}">
  <i class="bi bi-exclamation-triangle me-1"></i><strong>Needs restart</strong>
</span>
    """) if container else ""


@register.simple_tag
def button_save_changes(container = None):
    return format_html(f"""
<span id="container-save-{cid(container)}" class="badge rounded-pill bg-danger text-light p-3 d-none" role="button"
      onclick="save_container_config('{cid(container)}')">
  <i class="bi bi-save me-1"></i><span>Save changes</span>
</span>
    """)


@register.simple_tag
def button_delete_container(container = None):
    if not container or hasattr(container, "report"):
        return "" #FIXME: space holder!
    link = reverse('container:destroy', args = [container.id])
    msg = f"Are you sure you want to drop your container {container}?"
    return format_html(f"""
<a href="{link}" onclick="return confirm('{msg}');" role="button" class="badge rounded-pill text-bg-danger border p-2"><span class="oi oi-trash" aria-hidden="true" data-toggle="tooltip" title="Remove {container.name}"></span></a>
    """)


@register.simple_tag
def button_start(container = None, id_suffix = ''):
    return format_html(f"""
<div id="container-start-{container.id}{id_suffix}">
    <button class="badge rounded-pill text-bg-success border p-2" name="start"
            data-toggle="tooltip" title="Start environment {container.name}"
            onclick="handle_click('start', {container.id})">
      <span class="bi bi-lightning" aria-hidden="true" role="status"></span>
    </button>
    <button class="badge rounded-pill text-bg-warning border p-2" name="restart"
            data-toggle="tooltip" title="Restart environment {container.name}"
            onclick="handle_click('restart', {container.id})">
      <span class="bi bi-bootstrap-reboot" aria-hidden="true"></span>
    </button>
    <button class="badge rounded-pill text-bg-success border p-2" name="busy" disabled>
      <span class="spinner-grow spinner-grow-sm" aria-hidden="true" role="status"></span>
    </button>
    <button class="badge rounded-pill text-bg-secondary border p-2" name="default" disabled>
      <span class="bi bi-lightning" aria-hidden="true"></span>
    </button>
</div>
    """) if container else ""


@register.simple_tag
def button_stop(container = None, id_suffix = ''):
    return format_html(f"""
<div id="container-stop-{container.id}{id_suffix}">
    <button class="badge rounded-pill text-bg-danger border p-2" name="stop" 
            data-toggle="tooltip" title="Stop environment {container.name}"
            onclick="handle_click('stop', {container.id})">
      <span class="bi bi-x-lg" aria-hidden="true"></span>
    </button>
    <button class="badge rounded-pill text-bg-danger border p-2" name="disabled" disabled>
      <span class="bi bi-x-lg" aria-hidden="true"></span>
    </button>
    <button class="badge rounded-pill text-bg-danger border p-2" name="default"
            onclick="handle_click('stop', {container.id})">
      <span class="spinner-grow spinner-grow-sm" aria-hidden="true" role="status"></span>
    </button>
</div>
    """) if container else ""


@register.simple_tag
def button_open(container, id_suffix = ''):
    link = reverse('container:open', args = [container.id])
    return format_html(f"""
<span id="container-open-{container.id}{id_suffix}">
    <button class="badge rounded-pill text-bg-success border p-2" name="open"
            data-toggle="tooltip" title="Jump to environment {container.name}"
            onclick="handle_click('open', '{link}')">
      <span class="oi oi-external-link" aria-hidden="true"></span>
    </button>
    <button class="badge rounded-pill text-bg-secondary border p-2" name="default" disabled>
      <span class="oi oi-external-link" aria-hidden="true"></span>
    </button>
</span>
    """)


@register.simple_tag
def button_fetchlogs(container = None, id_suffix = ''):
    return format_html(f"""
<span id="container-log-{container.id}{id_suffix}">
    <button class="badge rounded-pill text-bg-info border p-3 me-2" name="fetch"
        data-toggle="tooltip" title="Click to retrieve latest container logs" data-placement="bottom"
        onclick='ContainerLogs.openModal({container.id})'>
        <span class="bi bi-heart-pulse"></span>
    </button>
    <button class="badge rounded-pill text-bg-secondary border p-3 me-2" name="default" disabled>
        <span class="bi bi-heart-pulse"></span>
    </button>
</span>
    """) if container else ""


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


