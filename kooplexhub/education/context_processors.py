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
    return {}
#FIXME:    empty = []
#FIXME:    ungrouped = {}
#FIXME:    for c in user.profile.courses_taught():
#FIXME:        G = g.groups
#FIXME:        if len(G) > 0 and None in G:
#FIXME:        students = set([ s.user for s in c.studentbindings ])
#FIXME:        for g in c.groups:
#FIXME:            group_students = g.students()
#FIXME:            if len(group_students):
#FIXME:                students.difference_update(group_students)
#FIXME:            else:
#FIXME:                empty.append(f'{g.name} ({g.course.name})')
#FIXME:        if len(students) and len(c.groups):
#FIXME:            ungrouped[c.name] = [ f'{s.first_name} {s.last_name}' for s in students ]
#FIXME:    return {
#FIXME:            'empty_course_groups': empty,
#FIXME:            'ungrouped_course_students': ungrouped,
#FIXME:            }

def active_tab(request):
    active_tab = request.COOKIES.get('active_tab', None)
    return { 'active_tab': active_tab } if active_tab else {}
