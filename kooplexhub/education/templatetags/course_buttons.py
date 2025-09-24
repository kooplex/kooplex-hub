from django import template
from django.template.loader import render_to_string

register = template.Library()


@register.simple_tag
def get_uabind_value(UAbind_dict, user_id, assignment_id):
    """
    Fetches the value of UAbind.x for a given (user_id, assignment_id).
    """
    from education.models import UserAssignmentBinding
    return render_to_string('education/assignment/button_handle_student.html', {
        "assignment": UserAssignmentBinding(),
        "aid": assignment_id,
        "uid": user_id,
        "state": UAbind_dict.get((user_id, assignment_id), UserAssignmentBinding.ST_QUEUED)
        })


@register.inclusion_tag("widgets/table_users.html")
def render_attendees(course=None, user=None):
    from ..tables import TableStudentsAndTeachers
    return {"pk": getattr(course, 'pk', None), "table": TableStudentsAndTeachers(course.userbindings.exclude(user=user)), 'editable': True} if course else {}
