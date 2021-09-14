from kooplexhub import settings
from .models import UserAssignmentBinding, UserCourseBinding

def assignment_warnings(request):
    user = request.user
    return { 
        'due_assignments': UserAssignmentBinding.objects.filter(user = user, state = UserAssignmentBinding.ST_WORKINPROGRESS)
    } if user.is_authenticated else {}


def warnings(request):
    user = request.user
    return { 
        'unbound_courses': [ ucb.course for ucb in UserCourseBinding.objects.filter(user = user).exclude(course__coursecontainerbinding__container__user = user) ],
    } if user.is_authenticated else {}

def group_warnings(request):
    user = request.user
    if not user.is_authenticated:
        return {}
    empty = []
    ungrouped = {}
    for c in user.profile.courses_taught():
        students = set([ s.user for s in c.studentbindings ])
        for g in c.groups:
            group_students = g.students()
            if len(group_students):
                students.difference_update(group_students)
            else:
                empty.append(f'{g.name} ({g.course.name})')
        if len(students) and len(c.groups):
            ungrouped[c.name] = [ f'{s.first_name} {s.last_name}' for s in students ]
    return {
            'empty_course_groups': empty,
            'ungrouped_course_students': ungrouped,
            }

def active_tab(request):
    active_tab = request.COOKIES.get('active_tab', None)
    return { 'active_tab': active_tab } if active_tab else {}
