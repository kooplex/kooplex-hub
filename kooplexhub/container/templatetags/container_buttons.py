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

def inclusion_tag_ex(template_name, **tag_kwargs):
    """
    Extended inclusion_tag that:
      - attaches .template_name to the returned tag function
      - attaches .render(*args, **kwargs) to render server-side
      - preserves support for takes_context / name / extra_context

    Usage:
      @inclusion_tag_ex("path/to/tpl.html")
      def mytag(arg1, arg2=False): ...

      html = mytag.render(obj, arg2=True)   # in Python (e.g., WS consumer)
    """
    takes_context = tag_kwargs.get("takes_context", False)

    def _decorator(func):
        # Register the real inclusion tag with Django
        tag_func = register.inclusion_tag(template_name, **tag_kwargs)(func)

        # Attach metadata & original callable for direct use
        tag_func.template_name = template_name
        tag_func.original_func = func

        # Add a convenient server-side renderer
        def _render(*args, context=None, **kwargs):
            """
            Render the inclusion tag to HTML without going through a template.
            If the original tag declared takes_context=True, you may pass a dict
            via `context=`; otherwise it will use {}.
            """
            if takes_context:
                # First arg must be a Context-like mapping
                ctx = context or {}
                ctx_dict = dict(ctx) if not isinstance(ctx, dict) else ctx
                context_dict = func(ctx_dict, *args, **kwargs)
            else:
                context_dict = func(*args, **kwargs)
            return render_to_string(template_name, context_dict)

        tag_func.render = _render
        return tag_func

    return _decorator



@inclusion_tag_ex("container/button/start.html")
def button_start(container):
    return {"container": container}

@inclusion_tag_ex("container/button/stop.html")
def button_stop(container):
    return {"container": container}

@inclusion_tag_ex("container/button/fetchlogs.html")
def button_fetchlogs(container):
    return {"container": container}

@inclusion_tag_ex("container/button/image.html")
def button_image(obj, attr="image", callback=''):
    return {"pk": getattr(obj, 'pk', None), "image": getattr(obj, attr, ""), "callback": callback}

@inclusion_tag_ex("container/button/open.html")
def button_open(container):
    return {"container": container}

@inclusion_tag_ex("container/button/restart.html")
def button_restart(container):
    return {"container": container}

@inclusion_tag_ex("container/badge_state.html")
def indicator_state(container):
    return {"container": container}

@inclusion_tag_ex("container/button/teleport.html")
def button_teleport(container):
    return {"container": container, 'icon': static('teleport.ico')}

@inclusion_tag_ex("container/button/seafile.html")
def button_seafile(container):
    return {"container": container, 'icon': static('seafile.png')}

@inclusion_tag_ex("container/button/mount.html")
def button_mount(container, callback):
    return {"container": container, "callback": callback}

@inclusion_tag_ex("container/button/resources.html")
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




