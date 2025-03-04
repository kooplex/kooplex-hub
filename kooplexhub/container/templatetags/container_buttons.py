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
def button_view(view, container, show_name=False):
    return view.render_open_html(container, show_name) if view and container else ""

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


@register.simple_tag
def container_resources(container = None):
    geta = lambda container, attr: getattr(container, attr, None) if container else None
    return render_to_string("widgets/widget_container_resources.html", {
        "container": container,
        "node": geta(container, 'node'),
        "cpurequest": geta(container, 'cpurequest'),
        "gpurequest": geta(container, 'gpurequest'),
        "memoryrequest": geta(container, 'memoryrequest'),
        "idletime": geta(container, 'idletime'),
        })


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


