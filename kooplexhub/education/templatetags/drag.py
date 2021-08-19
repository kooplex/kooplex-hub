import json

from django import template
from django.utils.html import format_html


register = template.Library()

@register.filter(name = 'drag')
def drag(usercoursebinding):
    u = usercoursebinding.user
    return format_html(f"""
<p class="drag btn btn-default" id="{usercoursebinding.id}" data-bs-toggle="tooltip" title="username: {u.username}\nemail: {u.email}">{u.first_name} {u.last_name}</p>
    """)


@register.filter(name = 'dropgroup')
def dropgroup(grpmap):
    grp, students = grpmap
    student_buttons = ""
    ucb_ids = []
    for ucb in students:
        student_buttons += drag(ucb)
        ucb_ids.append( int(ucb.id) )
    n = len( ucb_ids )
    hidden = json.dumps(ucb_ids)
    return format_html(f"""
<div>
  <div id="dropzone-{grp.id}" class="dropzone">
    <h6 data-bs-toggle="tooltip" title="{grp.description}">Group {grp.name} (member count: <span id="cnt-{grp.id}">{n}</span>)</h6>
    {student_buttons}
    <input type="hidden" id="grp-{grp.id}" name="grp-{grp.id}" value='{hidden}'>
    <input type="hidden" id="before_grp-{grp.id}" name="before_grp-{grp.id}" value='{hidden}'>
  </div>
</div>
    """)

