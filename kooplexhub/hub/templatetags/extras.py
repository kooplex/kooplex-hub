from django import template
from django.utils.html import format_html
from django.urls import reverse

from education.models import UserCourseBinding

register = template.Library()

@register.simple_tag(name = 'title')
def title(*argv):
    t = " ".join(argv)
    return format_html(f"""<h6 class="mb-4">{t}</h6>""")


@register.simple_tag(name = 'apply_cancel')
def apply_cancel(hide_apply = False, label_apply = 'Submit', hide_cancel = True, label_cancel = 'Cancel'):
    submit = "" if hide_apply else f"""<div><button type="submit" class="btn btn-primary" name="button" value="apply">{label_apply}</button></div>"""
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
        'info': [],
        'success': [],
        'error': [],
    }
    for message in messages:
        if messages.level == 25:
            data['success'].append(message)
        elif message.level == 20:
            data['info'].append(message)
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
      <strong class="me-auto">Messages</strong>
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


