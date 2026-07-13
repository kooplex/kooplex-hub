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

@register.simple_tag(takes_context=True)
def button_image(
    context,
    obj=None,
    model=None,
    attr="image",
    value=None,
    disabled="",
    **kwargs,
):
    pk = getattr(obj, "pk", None)

    if obj is not None:
        image = getattr(obj, attr, value)
    else:
        image = value


    image_modal_url = (
        getattr(obj, "image_modal_url", None)
        if pk and not disabled
        else None
    )

    return render_to_string(
        "container/button/image.html",
        {
            "pk": pk,
            "image": image,
            "model": model,
            "attr": attr,
            "disabled": disabled,
            "image_modal_url": image_modal_url,
        },
        request=context.get("request"),
    )

@inclusion_tag_ex("container/button/open.html")
def button_open(container):
    return {"container": container}

@inclusion_tag_ex("container/button/restart.html")
def button_restart(container):
    return {"container": container}

@inclusion_tag_ex("container/badge_state.html")
def indicator_state(container):
    return {"container": container}

@register.simple_tag
def button_teleport(container=None, **kwargs):
    image = getattr(container, 'image', None)
    if image and image.imagetype != image.ImageType.PROJECT:
        return ""
    return render_to_string("hub/buttons/toggle.html",  {
        "on": getattr(container, 'start_teleport', kwargs.get('value', False)), 
        "pk": getattr(container, 'pk', None), "model": "container",
        "attr": "start_teleport",
        'icon': static('container/img/teleport.ico')
    })

@register.simple_tag
def button_seafile(container=None, **kwargs):
    image = getattr(container, 'image', None)
    if image and image.imagetype != image.ImageType.PROJECT:
        return ""
    return render_to_string("hub/buttons/toggle.html", {
        "on": getattr(container, 'start_seafile', kwargs.get('value', False)), 
        "pk": getattr(container, 'pk', None), "model": "container", "model": "container",
        "attr": "start_seafile",
        'icon': static('container/img/seafile.png')
    })


@register.simple_tag(takes_context=True)
def button_mount(context, obj=None, disabled="", **kwargs):
    pk = getattr(obj, "pk", None)

    mounts_modal_url = (
        getattr(obj, "mounts_modal_url", None)
        if pk and not disabled
        else None
    )

    mount_summary = getattr(obj, "mount_summary", None)
    if callable(mount_summary):
        mount_summary = mount_summary()

    if mount_summary is None:
        mount_summary = {
            "project_count": 0,
            "course_count": 0,
            "volume_count": 0,
            "tooltip": "No custom mounts.",
        }

    return render_to_string(
        "container/button/mount.html",
        {
            "obj": obj,
            "disabled": disabled,
            "mounts_modal_url": mounts_modal_url,
            "mount_summary": mount_summary,
        },
        request=context.get("request"),
    )


@register.simple_tag
def button_resource_node(container=None, **kwargs):
    node=getattr(container, 'node', kwargs.get('value'))
    return render_to_string("container/button/resource_attribute.html", {
        "pk": getattr(container, 'pk', None),
        "attribute": "node",
        "hidden": not node,
        "icon": "bi bi-pc",
        "value": node,
    })

@register.simple_tag
def button_resource_cpurequest(container=None, **kwargs):
    cpurequest = getattr(container, 'cpurequest', kwargs.get('value'))
    return render_to_string("container/button/resource_attribute.html", {
        "pk": getattr(container, 'pk', None),
        "attribute": "cpurequest",
        "hidden": not cpurequest,
        "icon": "bi bi-cpu",
        "value": cpurequest,
    })

@register.simple_tag
def button_resource_gpurequest(container=None, **kwargs):
    gpurequest = getattr(container, 'gpurequest', kwargs.get('value'))
    return render_to_string("container/button/resource_attribute.html", {
        "pk": getattr(container, 'pk', None),
        "attribute": "gpurequest",
        "hidden": not gpurequest or gpurequest == 0,
        "icon": "bi bi-gpu-card",
        "value": gpurequest,
    })

@register.simple_tag
def button_resource_memoryrequest(container=None, **kwargs):
    memoryrequest = getattr(container, 'memoryrequest', kwargs.get('value'))
    return render_to_string("container/button/resource_attribute.html", {
        "pk": getattr(container, 'pk', None),
        "attribute": "memoryrequest",
        "hidden": not memoryrequest,
        "icon": "bi bi-memory",
        "value": memoryrequest,
        "unit": "GB",
    })

#@register.simple_tag
#def button_resource_idletime(container=None, **kwargs):
#    idletime = getattr(container, 'idletime', kwargs.get('value'))
#    return render_to_string("container/button/resource_attribute.html", {
#        "pk": getattr(container, 'pk', None),
#        "attribute": "idletime",
#        "hidden": not idletime,
#        "icon": "bi bi-clock-history",
#        "value": idletime,
#        "unit": "h",
#    })

@register.simple_tag
def button_view(view, container, show_name=False):
    try:
        _link = reverse('container:open_serviceview', args = [container.id, view.id])
    except:
        return "<i class='bi bi-eye-slash'></i>"
    return render_to_string("container/button/view.html", {"container": container, "view": view, "link": _link, "show_name": show_name})




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




