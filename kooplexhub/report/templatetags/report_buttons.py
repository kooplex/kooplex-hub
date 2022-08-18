from django import template
from django.utils.html import format_html
from django.urls import reverse

register = template.Library()


@register.simple_tag(name = 'r_scope')
def r_scope(report):
    if report.scope == report.SC_PRIVATE:
        return format_html(f"""
<i class="oi oi-key" aria-hidden="true" data-bs-toggle="tooltip" title="Private report" data-placement="top"></i>
        """)
    elif report.scope == report.SC_INTERNAL:
        return format_html(f"""
<i class="bi bi-people" aria-hidden="true" data-bs-toggle="tooltip" title="Internal report" data-placement="top"></i>
        """)
    elif report.scope == report.SC_PUBLIC:
        return format_html(f"""
<i class="oi oi-cloud" aria-hidden="true" data-bs-toggle="tooltip" title="Public report" data-placement="top"></i>
        """)
    else:
        return "-"


@register.simple_tag
def button_report_open(report):
    link = reverse('report:open', args = [report.id])
    return format_html(f"""
<a href="{link}" target="_blank" role="button" class="btn btn-success btn-sm" data-toggle="tooltip" title="Access report {report.name}"><span class="oi oi-external-link" aria-hidden="true"></span></a>
    """)


@register.simple_tag
def button_report_conf(report, user):
    if report.creator == user:
        link = reverse('report:configure', args = [ report.id ])
        return format_html(f"""
<a href="{link}" role="button" class="btn btn-secondary btn-sm"><span class="oi oi-wrench" aria-hidden="true" data-toggle="tooltip" title="Settings of report {report.name}." data-placement="top" ></span></a>
        """)
    else:
        return format_html(f"""
<a href="#" role="button" class="btn btn-secondary btn-sm disabled"><span class="oi oi-wrench" aria-hidden="true" data-toggle="tooltip" title="You don't have permission to configure report {report.name}." data-placement="top" ></span></a>
        """)




@register.simple_tag
def button_report_delete(report, user):
    if report.creator == user:
        link = reverse('report:delete', args = [ report.id ])
        return format_html(f"""
<a href="{link}" role="button" class="btn btn-danger btn-sm" onclick="return confirm('Are you sure?');"><span class="oi oi-trash" aria-hidden="true" data-toggle="tooltip" title="Delete report {report.name}." data-placement="top"></span></a>
    """)
    else:
        return format_html(f"""
<a href="#" role="button" class="btn btn-secondary btn-sm disabled"><span class="oi oi-trash" aria-hidden="true" data-toggle="tooltip" title="You don't have permission to delete report {report.name}." data-placement="top"></span></a>
    """)


