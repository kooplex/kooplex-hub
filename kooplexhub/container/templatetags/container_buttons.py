from django import template
from django.utils.html import format_html
from django.template.loader import render_to_string
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


#FIXME: these 2 templates are very much alike, could be merged
@register.simple_tag
def button_teleport(container = None):
    return render_to_string("widgets/button_teleport.html", {"container": container, 'icon': static('teleport.ico')}) if container else ""


@register.simple_tag
def button_seafile(container = None):
    return render_to_string("widgets/button_seafile.html", {"container": container, 'icon': static('seafile.png')}) if container else ""


@register.simple_tag
def container_image(obj, attr="image"):
    return render_to_string("widgets/widget_image.html", {"pk": getattr(obj, 'id', None), "image": getattr(obj, attr, "")})


#FIXME be a templated widget
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
  <button class="badge rounded-pill text-dark p-2 border border-1 border-dark w-100 text-start" role="button">
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
    return render_to_string("widgets/widget_mount.html", {"container": container })


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


