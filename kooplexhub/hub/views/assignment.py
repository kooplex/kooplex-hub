import re
import datetime
import logging

from django.conf.urls import url
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import redirect

from hub.models import Course, UserCourseBinding, Assignment, UserAssignmentBinding

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
    can_studentsubmit = bool(request.POST.get("cansubmit"))
    try:
        assert len(name), "You need to provide a name"
        assert len(course_flags), "You need to select at least one course flag"
        course = Course.objects.get(id = course_id)
        goodflags = set([ b.flag for b in UserCourseBinding.objects.filter(course = course, user = user, is_teacher = True) ])
        course_flags.intersection_update(goodflags)
        assert len(course_flags), "You are not authorized to save assignment to course flags provided"
#FIXME: valid/expiry
        for flag in course_flags:
            Assignment.objects.create(course = course, flag = flag, name = name, creator = user, description = description, folder = folder, can_studentsubmit = can_studentsubmit)
    except Exception as e:
        logger.error(e)
        messages.error(request, 'Cannot fully register assignment -- %s' % e)
    messages.info(request, 'Assignments are registered for course %s and flag %s' % (course.courseid, ", ".join(course_flags)))
    return redirect('teaching:list')


@login_required
def studentsubmit(request):
    """Handle assignment submission"""
    user = request.user
    userassignmentbinding_ids = request.POST.getlist('userassignmentbindingid')
    for binding_id in userassignmentbinding_ids:
        try:
            binding = UserAssignmentBinding.objects.get(id = binding_id, user = user)
            binding.state = UserAssignmentBinding.ST_SUBMITTED
            binding.submitted_at = datetime.datetime.now()
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
        course = None
    for assignment_id in assignment_ids:
        try:
            assignment = Assignment.objects.get(id = assignment_id, course = course)
            UserCourseBinding.objects.get(user = user, course = course, flag = assignment.flag, is_teacher = True)
            counter = 0
            for binding in UserAssignmentBinding.objects.filter(assignment = assignment):
                #FIXME: we may double check state and skip some bindings
                binding.state = UserAssignmentBinding.ST_COLLECTED
                binding.submitted_at = datetime.datetime.now()
                binding.save()
                counter += 1
            messages.info(request, '%d assignments %s for course %s and flag %s are collected' % (counter, assignment.name, assignment.course.courseid, assignment.flag))
        except Exception as e:
            logger.error(e)
            messages.error(request, 'Cannot mark assignment collected -- %s' % e)
    return redirect('teaching:list')


@login_required
def markcorrection(request):
    """Mark assignments to correct"""
    user = request.user
    userassignmentbinding_ids = request.POST.getlist('userassignmentbindingid')
    for binding_id in userassignmentbinding_ids:
        try:
            binding = UserAssignmentBinding.objects.get(id = binding_id, state = UserAssignmentBinding.ST_SUBMITTED)
            UserCourseBinding.objects.get(user = user, course = binding.assignment.course, flag = binding.assignment.flag, is_teacher = True)
            binding.state = UserAssignmentBinding.ST_CORRECTING
            binding.save()
            messages.info(request, '%s\'s assignment %s for course %s and flag %s is marked for being corrected' % (binding.user.username, binding.assignment.name, binding.assignment.course.courseid, binding.assignment.flag))
        except Exception as e:
            logger.error(e)
            messages.error(request, 'Cannot mark assignment for correction -- %s' % e)
    return redirect('teaching:list')


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
            binding.corrected_at = datetime.datetime.now()
            binding.save()
            messages.info(request, '%s\'s assignment %s for course %s and flag %s is marked corrected' % (binding.user.username, binding.assignment.name, binding.assignment.course.courseid, binding.assignment.flag))
        except Exception as e:
            logger.error(e)
            messages.error(request, 'Cannot mark assignment corrected -- %s' % e)
    return redirect('teaching:list')


urlpatterns = [
    url(r'new/?$', new, name = 'new'),
    url(r'submit/?$', studentsubmit, name = 'submit'),
    url(r'collect/?$', teachercollect, name = 'collect'),
    url(r'correct/?$', markcorrection, name = 'correct'),
    url(r'feedback/?$', markcorrected, name = 'feedback'),
]


