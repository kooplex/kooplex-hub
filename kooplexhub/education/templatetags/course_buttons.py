from django import template
from django.utils.html import format_html
from django.urls import reverse
from django.template.defaultfilters import truncatechars

from hub.templatetags.extras import render_user
from ..models import Course

register = template.Library()

cid = lambda course: course.id if course else "new"


@register.simple_tag
def course_image(course = None):
    if course and course.preferred_image:
        iid = course.preferred_image.id
        ihn = truncatechars(course.preferred_image.hr, 20)
    else:
        iid = -1
        ihn = "Select image..."
    return format_html(f"""
<button data-pk="{cid(course)}" data-field="image" data-orig="{iid}" 
      class="badge rounded-pill p-3 border border-2 border-dark flex-grow-1 text-start text-dark" 
      onclick="ImageSelection.openModal('{cid(course)}', {iid}, 'preferred_image')" role="button">
  <i class="ri-image-2-line me-2"></i><span name="name" data-pk="{cid(course)}">{ihn}</span>
</button>
    """)


@register.simple_tag
def button_course_delete(course = None):
    if course:
        #FIXME???: implement link = reverse('course:delete', args = [ cid(course) ])
        link = ''
        return format_html(f"""
<a href="{link}" role="button" class="badge rounded-pill text-bg-danger border text-light p-3" onclick="return confirm('Are you sure?');"><span class="oi oi-trash" aria-hidden="true" data-toggle="tooltip" title="Delete course {course.name}." data-placement="top"></span></a>
        """)
    else:
        return ""


