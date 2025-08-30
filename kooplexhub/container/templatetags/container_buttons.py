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

@register.inclusion_tag("container/button/start.html")
def button_start(container):
    return {"container": container}

@register.inclusion_tag("container/button/stop.html")
def button_stop(container):
    return {"container": container}

@register.inclusion_tag("container/button/fetchlogs.html")
def button_fetchlogs(container):
    return {"container": container}

@register.inclusion_tag("container/button/image.html")
def button_image(container):
    return {
        "pk": container.pk, 
        "image": getattr(container, 'image', None),
        "callback": 'wss_containerconfig.register_changes',
    }

@register.inclusion_tag("container/button/open.html")
def button_open(container):
    return {"container": container}

@register.inclusion_tag("container/button/restart.html")
def button_restart(container):
    return {"container": container}

@register.inclusion_tag("container/badge_state.html")
def indicator_state(container):
    return {"container": container}

@register.inclusion_tag("container/button/teleport.html")
def button_teleport(container):
    return {"container": container, 'icon': static('teleport.ico')}

@register.inclusion_tag("container/button/seafile.html")
def button_seafile(container):
    return {"container": container, 'icon': static('seafile.png')}

@register.inclusion_tag("container/button/mount.html")
def button_mount(container, callback):
    return {"container": container, "callback": callback}

@register.inclusion_tag("container/button/resources.html")
def button_resources(container = None):
    #FIXME geta could be put in the template already?
    geta = lambda container, attr: getattr(container, attr, None) if container else None
    return {
        "container": container,
        "node": geta(container, 'node'),
        "cpurequest": geta(container, 'cpurequest'),
        "gpurequest": geta(container, 'gpurequest'),
        "memoryrequest": geta(container, 'memoryrequest'),
        "idletime": geta(container, 'idletime'),
        }


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
def button_view(view, container, show_name=False):
    #FIXME: get rid of model instance rendering
    return view.render_open_html(container, show_name) if view and container else ""

@register.simple_tag
def button_environment(obj = None):
    #FIXME: put html code in template dir
    pk = getattr(obj, 'id', None)
    return format_html(f"""
<button type="button" class="btn btn-secondary btn-sm rounded rounded-5 border border-2 border-dark" data-bs-toggle="modal" data-bs-target="#environmentsModal" data-id="{pk}">
    <i class="bi bi-boxes pe-1"></i>
    Environments
</button>
    """) if pk else ""


@register.simple_tag
def container_image(obj, attr="image", callback=None):
    return render_to_string("widgets/widget_image.html", {"pk": getattr(obj, 'id', None), "image": getattr(obj, attr, ""), "callback": callback or ''})


