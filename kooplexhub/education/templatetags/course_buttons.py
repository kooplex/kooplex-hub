from django import template
from django.utils.html import format_html
from django.urls import reverse
from django.template.defaultfilters import truncatechars

from hub.templatetags.extras import render_user
from ..models import Course

register = template.Library()

cid = lambda course: course.id if course else "new"


@register.simple_tag
def button_new_course(user):
    return format_html(f"""
<button type="button" class="btn btn-secondary btn-sm rounded rounded-5 border border-2 border-dark mb-2" data-bs-toggle="modal" data-bs-target="#newCourseModal" data-id="{user.id}">
    <i class="bi bi-plus-square pe-1"></i>
    Create new course...
</button>
    """)


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


@register.filter
def link_course_drop(course):
    #FIXME: return reverse('education:delete', args = [ cid(course) ]) if course else ""
    return ""


@register.filter
def link_new_ass(course):
    return reverse('education:newass', args = [ course.id ]) if course else ""
