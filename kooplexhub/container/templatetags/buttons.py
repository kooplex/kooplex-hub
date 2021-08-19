from django import template
from django.utils.html import format_html
from django.urls import reverse

register = template.Library()


@register.simple_tag
def container_image(container):
    i = container.image.name.split('/')[-1]
    if container.state == container.ST_NEED_RESTART:
        return format_html(f"""<span class="badge rounded-pill bg-danger"><i class="ri-image-2-line"></i>&nbsp; {i}</span>""")
    elif container.state == container.ST_RUNNING:
        return format_html(f"""<span class="badge rounded-pill bg-success"><i class="ri-image-2-line"></i>&nbsp; {i}</span>""")
    else:
        return format_html(f"""<span class="badge rounded-pill bg-secondary"><i class="ri-image-2-line"></i>&nbsp; {i}</span>""")


@register.simple_tag
def attachments(*args, **kwargs):
    a = kwargs.get('attachments', [])
    A = "\n".join(map(lambda x: f"{x.name} {x.description}", a))
    return format_html(f"""
<span class="badge rounded-pill bg-dark" aria-hidden="true" data-bs-toggle="tooltip" title="Attachments:\n{A}" data-placement="top"><i class="ri-attachment-2"></i> {len(a)}</span>
    """) if len(a) else ""


@register.simple_tag
def projects(*args, **kwargs):
    p = kwargs.get('projects', [])
    P = "\n".join(map(lambda x: f"{x.name} {x.description}", p))
    return format_html(f"""
<span class="badge rounded-pill bg-dark" aria-hidden="true" data-bs-toggle="tooltip" title="Projects:\n{P}" data-placement="top"><i class="ri-product-hunt-line"></i> {len(p)}</span>
    """) if len(p) else ""


@register.simple_tag
def courses(*args, **kwargs):
    c = kwargs.get('courses', [])
    C = "\n".join(map(lambda x: f"{x.name} {x.description}", c))
    return format_html(f"""
<span class="badge rounded-pill bg-dark" aria-hidden="true" data-bs-toggle="tooltip" title="Courses:\n{C}" data-placement="top"><i class="ri-copyright-line"></i> {len(c)}</span>
    """) if len(c) else ""


@register.simple_tag
def container_restart_reason(container):
    return format_html(f"""
<p class="card-text">
  <div class="alert alert-warning" role="alert">
    <strong>Needs restart:</strong> {container.restart_reasons}
  </div>
</p>
    """) if container.restart_reasons else ""


@register.simple_tag
def container_last_message(container):
    return format_html(f"""<p class="card-text"><strong>Last message:</strong> {container.last_message}</p>""") if container.last_message else ""


@register.simple_tag
def button_delete_container(container, next_page):
    link = reverse('container:destroy', args = [container.id, next_page])
    msg = f"Are you sure you want to drop your container {container}?"
    return format_html(f"""
<div class="float-end">
  <a href="{link}" onclick="return confirm('{msg}');" role="button" class="btn btn-danger btn-sm"><span class="oi oi-trash" aria-hidden="true" data-toggle="tooltip" title="Remove {container.name}"></span></a>
</div>
    """)


def button_start(container, next_page):
    #FIXME: patch_href()
    link = reverse('container:start', args = [container.id, next_page])
    return format_html(f"""
<a href="{link}" role="button" class="btn btn-outline-secondary btn-sm" data-toggle="tooltip" title="Start environment {container.name} onclick='return patch_href();'"><span class="oi oi-flash" aria-hidden="true"></span></a>
    """)


@register.simple_tag
def button_stop(container, next_page):
    if container.state == container.ST_RUNNING:
        link = reverse('container:stop', args = [container.id, next_page])
        return format_html(f"""
<a href="{link}" role="button" class="btn btn-danger btn-sm" data-toggle="tooltip" title="Stop environment {container.name}"><span class="oi oi-x" aria-hidden="true"></span></a>
        """)
    else:
        return format_html(f"""
<a href="#" role="button" class="btn btn-danger btn-sm disabled"><span class="oi oi-x" aria-hidden="true"></span></a>
        """)


@register.simple_tag
def button_restart(container, next_page):
    if container.state in [ container.ST_RUNNING, container.ST_ERROR ]:
        link = reverse('container:restart', args = [container.id, next_page])
        return format_html(f"""
<a href="{link}" role="button" class="btn btn-warning btn-sm" data-toggle="tooltip" title="Restart inconsistent environment {container.name}"><span class="bi bi-bootstrap-reboot" aria-hidden="true"></span></a>
        """)
    else:
        return format_html(f"""
<a href="#" role="button" class="btn btn-warning btn-sm disabled" data-toggle="tooltip" title="Restart inconsistent environment {container.name}"><span class="bi bi-bootstrap-reboot" aria-hidden="true"></span></a>
        """)


def button_open(container, next_page):
    link = reverse('container:open', args = [container.id, next_page])
    return format_html(f"""
<a href="{link}" target="_blank" role="button" class="btn btn-success btn-sm" data-toggle="tooltip" title="Access environment {container.name}"><span class="oi oi-external-link" aria-hidden="true"></span></a>
    """)


@register.simple_tag
def button_refreshlog(container, next_page):
    link = reverse('container:refreshlogs', args = [container.id])
    return format_html(f"""
<a href="{link}" role="button" class="btn btn-primary btn-sm" data-toggle="tooltip" title="Checkout the state of your service {container.name}"><span class="oi oi-reload" aria-hidden="true"></span></a>
    """)


@register.simple_tag
def button_start_open_restart(container, next_page):
    if container.state == container.ST_NEED_RESTART:
        return button_restart(container, next_page)
    elif container.state == container.ST_RUNNING:
        return button_open(container, next_page)
    elif container.state == container.ST_STARTING:
        return button_refreshlog(container, next_page)
    elif container.state == container.ST_ERROR:
        return format_html(f"""
<a href="#" role="button" class="btn btn-outline-warning btn-sm disabled" data-toggle="tooltip" title="Access erronous environment {container.name}"><span class="oi oi-flash" aria-hidden="true"></span></a>
        """)
    else:
        return button_start(container, next_page)


@register.simple_tag
def button_start_open(container, next_page):
    if container.state == container.ST_RUNNING:
        return button_open(container, next_page)
    elif container.state == container.ST_NOTPRESENT:
        return button_start(container, next_page)
    else:
        return format_html(f"""
<a href="#" role="button" class="btn btn-outline-warning btn-sm disabled" data-toggle="tooltip" title="Access erronous environment {container.name}"><span class="oi oi-flash" aria-hidden="true"></span></a>
        """)


@register.simple_tag
def button_configure(container):
    if container.state == container.ST_STARTING:
        return format_html(f"""
<a href="#" role="button" class="btn btn-secondary btn-sm"><span class="oi oi-wrench disabled" aria-hidden="true" data-toggle="tooltip" title="Your service is still starting up, cannot configure right now" data-placement="bottom"></span></a>
        """)
    else:
        link = reverse('container:configure', args = [container.id])
        return format_html(f"""
<a href="{link}" role="button" class="btn btn-secondary btn-sm"><span class="oi oi-wrench" aria-hidden="true" data-toggle="tooltip" title="Add/remove project to the service" data-placement="bottom"></span></a>
        """)


@register.simple_tag
def dropdown_start_open_stop(bindings, ancestor, ancestor_type, next_page):
    if len(bindings):
        items = ""
        for b in bindings:
            but_start_open = button_start_open(b.container, next_page)
            but_stop = button_stop(b.container, next_page)
            items += f"""
<li>
  <span class="dropdown-item">
    <div class="btn-group" role="group" aria-label="control buttons">
      <span>
        {but_start_open}
        {but_stop}
        {b.container.name}
      </span>
    </span>
  </div>
</li>
            """
        return format_html(f"""
<div class="dropdown" data-bs-toggle="tooltip" data-bs-placement="top" title="Service environments associated with {ancestor_type} {ancestor.name}">
  <a class="btn btn-outline-secondary dropdown-toggle btn-sm" type="button" id="dc-svcs-{ancestor.id}" data-bs-toggle="dropdown" aria-expanded="false">
    <i class="oi oi-terminal"></i>: {len(bindings)}
  </a>
  <ul class="dropdown-menu" aria-labelledby="dc-svcs-{ancestor.id}">
    {items}
  </ul>
</div>
        """)


