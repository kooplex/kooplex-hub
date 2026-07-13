from django import template
from django.template.loader import render_to_string
from django.urls import reverse


register = template.Library()

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


