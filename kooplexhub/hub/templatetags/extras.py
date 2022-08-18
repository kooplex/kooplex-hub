from django import template
from django.utils.html import format_html
from django.urls import reverse

from education.models import UserCourseBinding

register = template.Library()

@register.simple_tag(name = 'title')
def title(*argv):
    t = " ".join(argv)
    return format_html(f"""<h5 class="mb-4">{t}</h5>""")


@register.simple_tag(name = 'title_with_button')
def title_with_button(*argv, button_label = "Save all changes", button_icon = "bi bi-save", button_color = "btn-warning", button_id = None):
    t = " ".join(argv)
    bi = f'id="{button_id}"' if button_id else ''
    return format_html(f"""
<div class="container-fluid d-flex flex-column flex-md-row justify-content-between">
  <div><h5 class="mb-4">{t}</h5></div>
  <div><button {bi} type="submit" class="btn {button_color}" name="button" value="apply"><i class="{button_icon}"></i>&nbsp;{button_label}</button></div>
</div>""")


@register.simple_tag(name= 'render_user')
def render_user(user, prefix = "userid"):
    return format_html(f"""
<span id="{prefix}-{user.id}" data-toggle="tooltip" title="Username {user.username}." data-placement="top"><b>{user.first_name}</b> {user.last_name}</span>
    """)


@register.simple_tag(name = 'apply_cancel')
def apply_cancel(hide_apply = False, label_apply = 'Submit', icon_apply = None, color_apply="btn-warning", hide_cancel = True, label_cancel = 'Cancel'):
    ai = f'<i class="{icon_apply}"></i>&nbsp;' if icon_apply else ""
    submit = "" if hide_apply else f"""<div><button type="submit" class="btn {color_apply}" name="button" value="apply">{ai}{label_apply}</button></div>"""
    cancel = "" if hide_cancel else f"""<div><button type="submit" class="btn btn-secondary" name="button" value="cancel">{label_cancel}</button></div>"""
    return format_html(f"""
<div class="container-fluid d-flex flex-row justify-content-end mt-3">
{submit}{cancel}
</div>
    """)


@register.filter(name = 'join_links')
def join_links(courses, user):
    links = []
    for c in courses:
        ucb = UserCourseBinding.objects.get(course = c, user = user)
        link = reverse('education:autoaddcontainer', args = [ucb.id])
        links.append(f'<a href="{link}" data-toggle="tooltip" title="Following this link automatically creates a course environment.">{c.name} ({c.folder})</a>')
    return format_html(', '.join(links))


@register.filter(name = 'popupmessage')
def popumessage(messages):
    data = {
        'secondary': [],
        'success': [],
        'error': [],
    }
    for message in messages:
        if messages.level == 25:
            data['success'].append(message)
        elif message.level == 20:
            data['secondary'].append(message)
        elif message.level == 40:
            data['error'].append(message)
    div = ""
    for lbl, lst in data.items():
        if len(lst):
            div += """<div class="alert alert-{}" role="alert">{}</div>""".format(lbl, "<br>".join([str(m) for m in lst]))
    if div: 
        return format_html(f"""
<div class="position-fixed bottom-0 end-0 p-3" style="z-index: 11">
  <div id="infoMessages" class="toast fade show" role="alert" aria-live="assertive" aria-atomic="true">
    <div class="toast-header">
      <strong class="me-auto">Message</strong>
      <button id="closeButton" type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
    </div>
    <div class="toast-body">
    {div}
    </div>
  </div>
</div>
    """)
    else:
        return format_html("""<div id="infoMessages" class="hide"></div>""")


@register.simple_tag(name = 'render_date')
def render_date(date):
    return date.strftime("%Y-%m-%d %H:%M") if date else ''


@register.simple_tag(name = 'render_folder')
def render_folder(folder, subpath = None):
    import os
    if subpath:
        folder = os.path.join(folder, subpath)
    return format_html(f"""<span class="pillow"><i class="bi bi-folder" data-toggle="tooltip" title="Folder"></i>&nbsp;{folder}</span>""")
