from django import template
from django.utils.html import format_html
from django.urls import reverse

from education.models import UserCourseBinding

register = template.Library()

@register.filter(name = 'join_links')
def join_links(courses, user):
    links = []
    for c in courses:
        ucb = UserCourseBinding.objects.get(course = c, user = user)
        link = reverse('education:autoaddcontainer', args = [ucb.id])
        links.append(f'<a href="{link}" data-toggle="tooltip" title="Following this link automatically creates course environmnet">{c.name} ({c.folder})</a>')
    return format_html(', '.join(links))


@register.simple_tag
def layout_flip(is_list, callback):
    link = reverse(callback)
    icon = "oi-grid-two-up" if is_list else "oi-list"
    return format_html(f"""<a href="{link}" class="text-dark"><span class="oi {icon}"></span></a>""")


