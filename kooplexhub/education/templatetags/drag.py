import json

from django import template
from django.utils.html import format_html


register = template.Library()

@register.filter(name = 'drag')
def drag(u):
    return format_html(f"""
<p class="drag btn btn-default" id="{u.id}" data-bs-toggle="tooltip" title="username: {u.username}\nemail: {u.email}">{u.first_name} {u.last_name}</p>
    """)


@register.filter(name = 'dropgroup')
def dropgroup(grpmap):
    grp, students = grpmap
    if grp is None:
        gid = 'n'
        gname = 'Ungrouped students'
        gdesc = 'Drag student to a group'
    else:
        gid = grp.id
        gname = f'Group {grp.name}'
        gdesc = grp.description
    student_buttons = ""
    ids = []
    for s in students:
        student_buttons += drag(s)
        ids.append( int(s.id) )
    n = len( ids )
    hidden = json.dumps(ids)
    return format_html(f"""
<div id="dropzone-{gid}" class="dropzone">
  <h6 data-bs-toggle="tooltip" title="{gdesc}">{gname}</h6><p>student counter: <span id="cnt-{gid}">{n}</span></p>
  {student_buttons}
  <input type="hidden" id="grp-{gid}" name="grp-{gid}" value='{hidden}'>
  <input type="hidden" id="before_grp-{gid}" name="before_grp-{gid}" value='{hidden}'>
</div>
    """)

