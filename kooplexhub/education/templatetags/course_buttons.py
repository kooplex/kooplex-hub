from django import template
from django.utils.html import format_html
from django.template.loader import render_to_string
from django.urls import reverse
from django.template.defaultfilters import truncatechars

from hub.templatetags.extras import render_user
from ..models import Course

register = template.Library()


@register.simple_tag
def get_uabind_value(UAbind_dict, user_id, assignment_id):
    """
    Fetches the value of UAbind.x for a given (user_id, assignment_id).
    """
    from education.models import UserAssignmentBinding
    return render_to_string('widgets/assignment_conf_handlerbutton_per_student.html', {
        "assignment": UserAssignmentBinding(),
        "aid": assignment_id,
        "uid": user_id,
        "state": UAbind_dict.get((user_id, assignment_id), UserAssignmentBinding.ST_QUEUED)
        })



@register.simple_tag
def button_new_course(user):
    return format_html(f"""
<button type="button" class="btn btn-secondary btn-sm rounded rounded-5 border border-2 border-dark mb-2" data-bs-toggle="modal" data-bs-target="#newCourseModal" data-id="{user.id}">
    <i class="bi bi-plus-square pe-1"></i>
    Create new course...
</button>
    """)


@register.filter
def link_new_ass(course):
    return reverse('education:newass', args = [ course.id ]) if course else ""
