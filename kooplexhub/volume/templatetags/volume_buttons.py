from django import template
from django.utils.html import format_html
from django.urls import reverse

register = template.Library()


@register.simple_tag
def scope(volume):
    if volume.scope == volume.SCP_PRIVATE:
        return format_html(f"""
<i class="oi oi-key h6" aria-hidden="true" data-bs-toggle="tooltip" title="Private volume" data-placement="top"></i>
        """)
    else:
        return format_html(f"""
<i class="oi oi-cloud h6" aria-hidden="true" data-bs-toggle="tooltip" title="Public volume" data-placement="top"></i>
        """)


#@register.simple_tag
#def button_collaborator(volume, user):
#    upbs = x=volume.uservolumebindings
#    if len(upbs) > 1:
#        items = ""
#        for upb in upbs:
#            if upb.user != user:
#                items += f"""
#<li><a class="dropdown-item" href="#">{upb.user.username} ({upb.user.first_name} {upb.user.last_name})</a></li>
#                """
#        return format_html(f"""
#<div class="dropdown" data-bs-toggle="tooltip" data-bs-placement="top" title="Collaborators of volume {volume.name}">
#  <button class="btn btn-outline-secondary dropdown-toggle btn-sm" type="button" id="dc-collabs-{volume.id}" data-bs-toggle="dropdown" aria-expanded="false">
#    <i class="oi oi-people"></i>: {len(upbs)-1}
#  </button>
#  <ul class="dropdown-menu" aria-labelledby="dc-collabs-{volume.id}">{items}</ul>
#</div>
#        """)
#    else:
#        return ""
#


@register.simple_tag
def button_configure_volume(volume, user):
    if volume.is_admin(user):
        link = reverse('volume:configure', args = [volume.id])
        return format_html(f"""
<a href="{link}" role="button" class="btn btn-secondary btn-sm"><span class="oi oi-wrench" aria-hidden="true" data-toggle="tooltip" title="Update the name or description of this volume or administer access." data-placement="bottom"></span></a>
        """)
    else:
        return ""


@register.simple_tag
def button_volume_delete(volume, is_admin):
    link = reverse('volume:delete', args = [ volume.id ])
    if is_admin:
        return format_html(f"""
<a href="{link}" role="button" class="btn btn-danger btn-sm" onclick="return confirm('Are you sure you want to delete?');"><span class="oi oi-trash" aria-hidden="true" data-toggle="tooltip" title="Delete volume {volume.name}." data-placement="top"></span></a>
    """)
    else:
        return format_html(f"""
<a href="{link}" role="button" class="btn btn-danger btn-sm" onclick="return confirm('Are you sure you want to leave the volume?');"><span class="oi oi-trash" aria-hidden="true" data-toggle="tooltip" title="Delete volume {volume.name}." data-placement="top"></span></a>
    """)


#@register.simple_tag
#def number_square(x):
#    return format_html(f"""<span class="badge bg-secondary" data-bs-toggle="tooltip" title="The number of hidden volumes">{x}</span>""") if x else ""


