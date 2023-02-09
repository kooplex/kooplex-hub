from django import template
from django.utils.html import format_html
from django.urls import reverse

register = template.Library()

# {% load thumbnail %}

@register.simple_tag(name = 'r_scope')
def r_scope(report):
    if report.scope == report.SC_PRIVATE:
        return format_html(f"""
<i class="oi oi-key" aria-hidden="true" data-bs-toggle="tooltip" title="Private report" data-placement="top"></i>
        """)
    elif report.scope == report.SC_COLLABORATION:
        return format_html(f"""
<i class="bi bi-people-fill" aria-hidden="true" data-bs-toggle="tooltip" title="Collaboration report" data-placement="top"></i>
        """)
    elif report.scope == report.SC_INTERNAL:
        return format_html(f"""
<i class="bi bi-people" aria-hidden="true" data-bs-toggle="tooltip" title="Internal report, public to authenticated users" data-placement="top"></i>
        """)
    elif report.scope == report.SC_PUBLIC:
        return format_html(f"""
<i class="oi oi-cloud" aria-hidden="true" data-bs-toggle="tooltip" title="Public report" data-placement="top"></i>
        """)
    else:
        return "-"


@register.simple_tag
def button_side_modal_open(report, class_extra = ""):
    link = reverse('report:open', args = [ report.id ])
    return format_html(f"""
<a href="{link}" target="_blank" role="button" class="btn btn-success btn-sm {class_extra}"><span class="bi bi-folder2-open" aria-hidden="true" data-toggle="tooltip" title="Click to open report {report.name}" data-placement="top" ></span></a>
    """)


@register.simple_tag
def button_report_conf(report, user, class_extra = ""):
    if report.creator == user:
        link = reverse('report:configure', args = [ report.id ])
        return format_html(f"""
<a href="{link}" role="button" class="btn btn-secondary btn-sm {class_extra}"><span class="bi bi-wrench" aria-hidden="true" data-toggle="tooltip" title="Settings of report {report.name}." data-placement="top" ></span></a>
        """)
    else:
        return format_html(f"""
<div></div>
        """)


@register.simple_tag
def button_report_delete(report, user, class_extra = ""):
    if report.creator == user:
        link = reverse('report:delete', args = [ report.id ])
        return format_html(f"""
<a href="{link}" role="button" class="btn btn-danger btn-sm {class_extra}" onclick="return confirm('Are you sure?');"><span class="oi oi-trash" aria-hidden="true" data-toggle="tooltip" title="Delete report {report.name}." data-placement="top"></span></a>
    """)
    else:
        return format_html(f"""
<div></div>
    """)



# FIXME
@register.simple_tag
def image_report_open(report):
    link = reverse('report:open', args = [report.id])
    if report.thumbnail:
        return format_html(f"""""")
#        return format_html(f"""
#<img href="{link}" src="data:image/png;base64,{{report.thumbnail|decode}}" style="max-width: 100%; margin-left: auto; margin-right: auto; max-height: 80%; aspect-ratio: inherit; width: auto; height: auto;  display: block;" alt="thumbnail">
#    """)    
    else: # It should put the thumbnail of the category there
        return format_html(f"""
<img href="{link}" src="" style="max-width: 100%; margin-left: auto; margin-right: auto; max-height: 80%; aspect-ratio: inherit; width: auto; height: auto;  display: block;" alt="thumbnail">
    """)    
@register.simple_tag
def button_report_modal_open(report):
    link = reverse('report:open', args = [report.id])
    return format_html(f"""
<a href="{link}" target="_blank"> <button type="button" class="btn btn-success" data-bs-dismiss="modal">Open report</button></a>
    """)




#FIXME: is it used keep either this or button_side_modal_open
@register.simple_tag
def button_report_open(report):
    link = reverse('report:open', args = [report.id])
    return format_html(f"""
<a href="{link}"  target="_blank" ><span class="openlink"></span></a>
    """)

@register.simple_tag(name = 'r_help')
def r_help(modalid="", text="", imgsrc=""):
        return format_html(f"""
<div class="modal fade" id="exampleModalToggle{modalid}" aria-hidden="true" aria-labelledby="exampleModalToggleLabel" tabindex="-1">
    <div class="modal-dialog modal-dialog-centered">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title" id="exampleModalToggleLabel">Help report</h5>
          <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
        </div>
        <div class="modal-body">
        <p>{text}</p>
          <img class="print" src="/static/paintreport_menu.png" alt="print home">
        </div>
        <div class="modal-footer">
          <button class="btn btn-warning" data-bs-target="#exampleModalToggle2" data-bs-toggle="modal" data-bs-dismiss="modal">Next</button>
        </div>
      </div>
    </div>
  </div>
        """)


