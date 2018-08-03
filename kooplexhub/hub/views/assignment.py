import re
import datetime
import logging

from django.conf.urls import url
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import redirect

from hub.models import Course, UserCourseBinding, Assignment, UserAssignmentBinding
from kooplex.lib import now

logger = logging.getLogger(__name__)

@login_required
def new(request):
    """Create a new assignment"""
    user = request.user
    course_id = request.POST.get("course_id")
    course_flags = set([ None if f == "_" else f for f in request.POST.getlist("flag") ])
    name = request.POST.get("name").strip()
    description = request.POST.get("description").strip()
    folder = request.POST.get("folder")
    valid_date = request.POST.get('valid_from_0')
    valid_time = request.POST.get('valid_from_1', '00:00:00')
    expiry_date = request.POST.get('expires_at_0')
    expiry_time = request.POST.get('expires_at_1', '00:00:00')
    is_massassignment = bool(request.POST.get("massassignment"))
    can_studentsubmit = bool(request.POST.get("cansubmit"))
    try:
        assert len(name), "You need to provide a name"
        assert len(course_flags), "You need to select at least one course flag"
        course = Course.objects.get(id = course_id)
        goodflags = set([ b.flag for b in UserCourseBinding.objects.filter(course = course, user = user, is_teacher = True) ])
        course_flags.intersection_update(goodflags)
        assert len(course_flags), "You are not authorized to save assignment to course flags provided"
#FIXME: valid/expiry
        extra = {}
        if valid_date:
            extra['valid_from'] = "%s %s" % (valid_date, valid_time)
        if expiry_date:
            extra['expires_at'] = "%s %s" % (expiry_date, expiry_time)
        logger.debug("extra: %s" % extra)
        for flag in course_flags:
            Assignment.objects.create(course = course, flag = flag, name = name, creator = user, description = description, folder = folder, can_studentsubmit = can_studentsubmit, is_massassignment = is_massassignment, **extra)
        course_flags_str = map(lambda x: x if x else '_', course_flags)
        messages.info(request, 'Assignments are registered for course %s and flag %s' % (course.courseid, ", ".join(course_flags_str)))
    except Exception as e:
        logger.error(e)
        messages.error(request, 'Cannot fully register assignment -- %s' % e)
    return redirect('teaching:assignment', course_id)


@login_required
def studentsubmit(request):
    """Handle assignment submission"""
    user = request.user
    userassignmentbinding_ids = request.POST.getlist('userassignmentbindingid')
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
    return redirect('course:list')


@login_required
def teachercollect(request):
    """Handle assignment collection"""
    user = request.user
    assignment_ids = request.POST.getlist('assignmentid')
    course_id = request.POST.get('course_id')
    try:
        course = Course.objects.get(id = course_id)
    except Course.DoesNotExist:
        return redirect('teaching:list')
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
    return redirect('teaching:assignment', course_id)


@login_required
def markcorrection(request):
    """Mark assignments to correct"""
    user = request.user
    course_id = request.POST.get('course_id')
    userassignmentbinding_ids = request.POST.getlist('userassignmentbindingid')
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
    return redirect('teaching:assignment', course_id)


@login_required
def markcorrected(request):
    """Mark assignments to correct"""
    user = request.user
    userassignmentbinding_ids = request.POST.getlist('userassignmentbindingid')
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
    return redirect('teaching:list')


@login_required
def bind(request):
    from django.contrib.auth.models import User
    """Bind assignment and user"""
#FIXME: authorization!!!!!
    user = request.user
    for b in request.POST.getlist('binding'):
        assignment_id, user_id = b.split('-')
        try:
            assignment = Assignment.objects.get(id = assignment_id)
            student = User.objects.get(id = user_id)
        except Exception as e:
            logger.error("oops -- %s" % e)
            continue
        try:
            binding = UserAssignmentBinding.objects.get(user = student, assignment = assignment)
            logger.error("Will not create a duplicate %s" % binding)
            messages.error(request, "Prevented from creating a duplicate assignemt %s for student %s" % (assignment.name, student))
        except UserAssignmentBinding.DoesNotExist:
            UserAssignmentBinding.objects.create(user = student, assignment = assignment, expires_at = assignment.expires_at)
            messages.info(request, "Creating an assignemt %s for student %s" % (assignment.name, student))
    return redirect('teaching:list')


@login_required
def update(request):
    """Update assignment"""

urlpatterns = [
    url(r'new/?$', new, name = 'new'),
    url(r'submit/?$', studentsubmit, name = 'submit'),
    url(r'collect/?$', teachercollect, name = 'collect'),
    url(r'correct/?$', markcorrection, name = 'correct'),
    url(r'feedback/?$', markcorrected, name = 'feedback'),
    url(r'bind/?$', bind, name = 'bind'),
    url(r'update/?$', update, name = 'update'),
]


