import pytz
import datetime
import logging

from django.conf.urls import url
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import redirect, render
from django_tables2 import RequestConfig

from hub.models import Course, UserCourseBinding, Assignment, UserAssignmentBinding
from kooplex.lib import now, translate_date
from hub.forms import FormAssignment, T_BIND, T_COLLECT, T_CORRECT

logger = logging.getLogger(__name__)


@login_required
def assignmentform(request, course_id):
    """Renders assignment management form."""
    from hub.models import Course, UserCourseBinding
    user = request.user
    logger.debug('Rendering assignments.html')
    try:
        course = Course.objects.get(id = course_id)
        assert len(list(UserCourseBinding.objects.filter(user = user, course = course, is_teacher = True))) > 0, "%s is not a teacher of course %s" % (user, course)
        table_bind = T_BIND(course.bindableassignmentsNEW())  #FIXME: refactor rename
        RequestConfig(request).configure(table_bind)
        table_collect = T_COLLECT(course.collectableassignments())
        RequestConfig(request).configure(table_collect)
        table_correct = T_CORRECT(course.lookup_userassignmentbindings_submitted(user))
        RequestConfig(request).configure(table_correct)
        table_feedback = T_CORRECT(course.lookup_userassignmentbindings_correcting(user))
        RequestConfig(request).configure(table_feedback)
    except Exception as e:
        logger.error("Invalid request with course id %s and user %s -- %s" % (course_id, user, e))
        return redirect('indexpage')
    context_dict = {
        'course': course,
        'f_assignment': FormAssignment(user = user, course = course),
        't_bind': table_bind,
        't_collect': table_collect,
        't_correct': table_correct,
        't_feedback': table_feedback,
    }
    return render(request, 'edu/assignments.html', context = context_dict)

@login_required
def new(request):
    """Create a new assignment"""
    logger.debug(str(request.POST))
    user = request.user
    course_id = request.POST.get("course_id")
    course_flags = set([ None if f == "_" else f for f in request.POST.getlist("flags") ])
    name = request.POST.get("name").strip()
    description = request.POST.get("description").strip()
    folder = request.POST.get("folder")
    timenow = now()
    valid_from = translate_date(request.POST.get('valid_from')) or timenow
    expires_at = translate_date(request.POST.get('expires_at'))
    is_massassignment = bool(request.POST.get("is_massassignment"))
    can_studentsubmit = bool(request.POST.get("can_studentsubmit"))
    try:
        assert (valid_from - timenow).total_seconds() >= 0, "You try to chedule assignment behind time."
        assert len(name), "You need to provide a name"
        assert len(course_flags), "You need to select at least one course flag"
        course = Course.objects.get(id = course_id)
        goodflags = set([ b.flag for b in UserCourseBinding.objects.filter(course = course, user = user, is_teacher = True) ])
        course_flags.intersection_update(goodflags)
        assert len(course_flags), "You are not authorized to save assignment to course flags provided"
        extra = {}
        if expires_at:
            assert (expires_at - valid_from).total_seconds() >= 60, "Expiry is too close to handout. "
        for flag in course_flags:
            logger.debug("flag %s" % flag)
            Assignment.objects.create(
                course = course, 
                flag = flag, 
                name = name, 
                creator = user, 
                description = description, 
                folder = folder, 
                can_studentsubmit = can_studentsubmit, 
                is_massassignment = is_massassignment, 
                valid_from = valid_from,
                expires_at = expires_at
            )
        course_flags_str = map(lambda x: x if x else '_', course_flags)
        messages.info(request, 'Assignments are registered for course %s and flag %s' % (course.courseid, ", ".join(course_flags_str)))
        return redirect('list:teaching')
    except Exception as e:
        logger.error(e)
        messages.error(request, 'Cannot fully register assignment -- %s' % e)
        return redirect('assignment:manager', course_id)


@login_required
def studentsubmit(request):
    """Handle assignment submission"""
    user = request.user
    userassignmentbinding_ids = request.POST.getlist('selection')
    for binding_id in userassignmentbinding_ids:
        try:
            binding = UserAssignmentBinding.objects.get(id = binding_id, user = user)
            binding.state = UserAssignmentBinding.ST_SUBMITTED
            binding.submitted_at = now()
            binding.save()
            messages.info(request, '%s assignment submitted for course %s and flag %s' % (binding.assignment.name, binding.assignment.course.courseid, binding.assignment.flag))
        except Exception as e:
            logger.error(e)
            messages.error(request, 'Cannot fully submit assignment -- %s' % e)
    return redirect('list:courses')


@login_required
def teachercollect(request):
    """Handle assignment collection"""
    user = request.user
    assignment_ids = request.POST.getlist('selection')
    course_id = request.POST.get('course_id')
    try:
        course = Course.objects.get(id = course_id)
    except Course.DoesNotExist:
        return redirect('list:teaching')
    for assignment_id in assignment_ids:
        try:
            assignment = Assignment.objects.get(id = assignment_id, course = course)
            UserCourseBinding.objects.get(user = user, course = course, flag = assignment.flag, is_teacher = True)
            counter = 0
            for binding in UserAssignmentBinding.objects.filter(assignment = assignment):
                binding.do_collect()
                counter += 1
            messages.info(request, '%d assignments %s for course %s and flag %s are collected' % (counter, assignment.name, assignment.course.courseid, assignment.flag))
        except Exception as e:
            logger.error(e)
            messages.error(request, 'Cannot mark assignment collected -- %s' % e)
    return redirect('assignment:manager', course_id)


@login_required
def markcorrection(request):
    """Mark assignments to correct"""
    user = request.user
    course_id = request.POST.get('course_id')
    userassignmentbinding_ids = request.POST.getlist('selection')
    for binding_id in userassignmentbinding_ids:
        try:
            binding = UserAssignmentBinding.objects.get(id = binding_id)
            assert binding.state in [ UserAssignmentBinding.ST_SUBMITTED, UserAssignmentBinding.ST_COLLECTED ]
            assert binding.assignment.course.id == int(course_id), "Course id mismatch"
            UserCourseBinding.objects.get(user = user, course = binding.assignment.course, flag = binding.assignment.flag, is_teacher = True)
            binding.state = UserAssignmentBinding.ST_CORRECTING
            binding.corrector = user
            binding.save()
            messages.info(request, '%s\'s assignment %s for course %s and flag %s is marked for being corrected' % (binding.user.username, binding.assignment.name, binding.assignment.course.courseid, binding.assignment.flag))
        except Exception as e:
            logger.error(e)
            messages.error(request, 'Cannot mark assignment for correction -- %s' % e)
    return redirect('assignment:manager', course_id)


@login_required
def markcorrected(request):
    """Mark assignments to correct"""
    user = request.user
    userassignmentbinding_ids = request.POST.getlist('selection')
    for binding_id in userassignmentbinding_ids:
        try:
            binding = UserAssignmentBinding.objects.get(id = binding_id, state = UserAssignmentBinding.ST_CORRECTING)
            UserCourseBinding.objects.get(user = user, course = binding.assignment.course, flag = binding.assignment.flag, is_teacher = True)
            binding.state = UserAssignmentBinding.ST_FEEDBACK
            binding.corrected_at = now()
            binding.save()
            messages.info(request, '%s\'s assignment %s for course %s and flag %s is marked corrected' % (binding.user.username, binding.assignment.name, binding.assignment.course.courseid, binding.assignment.flag))
        except Exception as e:
            logger.error(e)
            messages.error(request, 'Cannot mark assignment corrected -- %s' % e)
    return redirect('list:teaching')


@login_required
def bind(request):
    from django.contrib.auth.models import User
    """Bind assignment and user"""
    user = request.user
    thetime = now()
    oopses = 0
    done = 0
    for br in request.POST.getlist('binding_representation'):
        user_id, assignment_id = br.split('_')
        try:
            assignment = Assignment.objects.get(id = assignment_id)
            student = User.objects.get(id = user_id)
            assert student in assignment.list_students_bindable(), "Cannot bind %s to %s" % (student, assignment)
            assert user.profile.is_courseteacher(assignment.course), "You are not a teacher of the course %s" % assignment.course
        except Exception as e:
            logger.error("oops -- %s" % e)
            oopses += 1
            continue
        try:
            binding = UserAssignmentBinding.objects.get(user = student, assignment = assignment)
            logger.error("Will not create a duplicate %s" % binding)
            messages.error(request, "Prevented from creating a duplicate assignment %s for student %s" % (assignment.name, student))
        except UserAssignmentBinding.DoesNotExist:
            pass
        valid_from = translate_date(request.POST.get('valid_from_%s' % br))
        expires_at = translate_date(request.POST.get('expires_at_%s' % br))
        UserAssignmentBinding.objects.create(user = student, assignment = assignment, valid_from = valid_from, expires_at = expires_at)
#FIXME> expiry check in model init!
        messages.info(request, "Creating an assignment %s for student %s" % (assignment.name, student))
    return redirect('list:teaching')


@login_required
def update(request):
    """Update assignment"""

urlpatterns = [
    url(r'(?P<course_id>\d+)$', assignmentform, name = 'manager'),
    url(r'new/?$', new, name = 'new'),
    url(r'submit/?$', studentsubmit, name = 'submit'),
    url(r'collect/?$', teachercollect, name = 'collect'),
    url(r'correct/?$', markcorrection, name = 'correct'),
    url(r'feedback/?$', markcorrected, name = 'feedback'),
    url(r'bind/?$', bind, name = 'bind'),
    url(r'update/?$', update, name = 'update'),
]


