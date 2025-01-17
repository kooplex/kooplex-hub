#FIXME    link = reverse('container:open', args = [container.id])
from django import template
from django.utils.html import format_html
from django.urls import reverse

from ..models import Container
from volume.models import Volume
from container.lib.cluster_resources_api import *
import pandas

from django.template.defaultfilters import truncatechars
from django.templatetags.static import static

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
        return "border-success"
    else:
        return "border-warning"


@register.simple_tag
def button_environment(obj = None):
    pk = getattr(obj, 'id', None)
    return format_html(f"""
<button type="button" class="btn btn-secondary btn-sm rounded rounded-5 border border-2 border-dark" data-bs-toggle="modal" data-bs-target="#environmentsModal" data-id="{pk}">
    <i class="bi bi-boxes pe-1"></i>
    Environments
</button>
    """) if pk else ""


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
    ico = static('teleport.ico')
    return format_html(f"""
<div id="container-teleport-{cid(container)}">
    <button class="badge rounded-pill border border-1 border-dark p-3 me-2 position-relative" name="grant"
            data-toggle="tooltip" title="Enable teleport login"
            onclick="teleportButtonClick('{cid(container)}', 'True')">
      <img src="{ico}" width="15px" alt="t">
      <span class="position-absolute top-0 start-100 translate-middle badge bg-secondary small">off</span>
    </button>
    <button class="badge rounded-pill border border-2 border-success p-3 me-2 position-relative" name="revoke"
            data-toggle="tooltip" title="Disable teleport login"
            onclick="teleportButtonClick('{cid(container)}', 'False')">
      <img src="{ico}" width="15px" alt="t">
      <span class="position-absolute top-0 start-100 translate-middle badge bg-success small">on</span>
    </button>
</div>
    """)


@register.simple_tag
def button_seafile(container = None):
    ico = static('seafile.png')
    return format_html(f"""
<div id="container-seafile-{cid(container)}">
    <button class="badge rounded-pill border border-1 border-dark p-3 me-2 position-relative" name="grant"
            data-toggle="tooltip" title="Mount cloud folders"
            onclick="seafileButtonClick('{cid(container)}', 'True')">
      <img src="{ico}" width="15px" alt="t">
      <span class="position-absolute top-0 start-100 translate-middle badge bg-secondary small">off</span>
    </button>
    <button class="badge rounded-pill border border-2 border-success p-3 me-2 position-relative" name="revoke"
            data-toggle="tooltip" title="Umount cloud folders"
            onclick="seafileButtonClick('{cid(container)}', 'False')">
      <img src="{ico}" width="15px" alt="t">
      <span class="position-absolute top-0 start-100 translate-middle badge bg-success small">on</span>
    </button>
</div>
    """)


@register.simple_tag
def container_image(container = None):
    if container:
        iid = container.image.id
        ihn = truncatechars(container.image.hr, 20)
    else:
        iid = -1
        ihn = "Select image..."
    return format_html(f"""
<button data-pk="{cid(container)}" data-field="image" data-orig="{iid}" 
      class="badge rounded-pill text-dark p-3 border border-1 border-dark flex-grow-1 text-start" 
      onclick="ImageSelection.openModal('{cid(container)}', {iid})" role="button">
  <i class="ri-image-2-line me-2"></i><span name="name" data-pk="{cid(container)}">{ihn}</span>
</button>
    """)


@register.simple_tag
def container_resources(container = None):
    _atlist = [ "node", "cpurequest", "gpurequest", "memoryrequest", "idletime"]
    geta = lambda container, attr: getattr(container, attr, None) if container else None
    atts = { a: geta(container, a) for a in _atlist }
    cn = container.name if container else ""
    hv = { a: "" if v else "d-none" for a, v in atts.items() }
    empty = "d-none" if len(_atlist)>list(atts.values()).count(None) else ""
    return format_html(f"""
<div id="container-resources-{cid(container)}"
      data-bs-toggle="tooltip" data-placement="bottom"
      title="Requested compute resources. Double click to tune."
      data-node="{atts['node']}" data-cpurequest="{atts['cpurequest']}" data-gpurequest="{atts['gpurequest']}"
      data-memoryrequest="{atts['memoryrequest']}" data-idletime="{atts['idletime']}"
      onclick="ComputeResourceSelection.openModal('{cid(container)}', \'{atts['node']}\')">
  <button class="badge rounded-pill text-dark p-3 border border-1 border-dark w-100 text-start" role="button">
    <span class="{hv['node']}" name="node"><i class="bi bi-pc me-1"></i><span name="node_name" class="me-2">{truncatechars(atts['node'], 6)}</span></span>
    <span class="{hv['cpurequest']}" name"cpu"><i class="bi bi-cpu me-1"></i><span name="node_cpu_request" class="me-2">{atts['cpurequest']}</span></span>
    <span class="{hv['gpurequest']}" name="gpu"><i class="bi bi-gpu-card me-1"></i><span name="node_gpu_request" class="me-2">{atts['gpurequest']}</span></span>
    <span class="{hv['memoryrequest']}" name="mem"><i class="bi bi-memory me-1"></i><span name="node_mem_request" class="me-2">{atts['memoryrequest']} GB</span></span>
    <span class="{hv['idletime']}" name="up"><i class="bi bi-clock-history me-1"></i><span name="node_idle" class="me-2">{atts['idletime']} h</span></span>
    <span class="{empty}" name="empty"><i class="bi bi-wrench-adjustable me-1"></i>default resources</span>
  </button>
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
        volume_ids=[v.id for v in container.volumes]
        v = len(volume_ids)
    else:
        volume_ids=[]
        p=v=c=0
    empty = "d-none" if p+v+c else ""
    return format_html(f"""
<button id="container-mounts-{cid(container)}" data-pk="{cid(container)}"
      class="badge rounded-pill p-3 border border-1 border-dark text-dark flex-grow-1 text-start" 
      data-bs-toggle="tooltip" data-placement="bottom"
      data-volumes="{volume_ids}"
      title="Requested filesystem resources. Double click to change mounts."
      onclick="FileResourceSelection.openModal('{cid(container)}')" role="button">
    <span class="{hs(p)}" name="project"><i class="ri-product-hunt-line me-1"></i><span name="project_count" class="me-2">{p}</span></span>
    <span class="{hs(c)}" name="course"><i class="ri-copyright-line me-1"></i><span name="course_count" class="me-2">{c}</span></span>
    <span class="{hs(v)}" name="volume"><i class="ri-database-2-line me-1"></i><span name="volume_count" class="me-2">{v}</span></span>
    <span class="{empty}" name="empty"><i class="bi bi-folder me-2"></i>default mounts</span>
</button>
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


