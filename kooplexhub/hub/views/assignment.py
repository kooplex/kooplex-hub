import pytz
import datetime
import logging

from django.db import transaction
from django.conf.urls import url
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import reverse
from django_tables2 import RequestConfig

#FIXME
from hub.models import Course, UserCourseCodeBinding as UserCourseBinding, Assignment, UserAssignmentBinding
from kooplex.lib import now, translate_date
from hub.forms import FormAssignment, T_BIND, T_COLLECT_ASSIGNMENT, T_COLLECT_UABINDING, T_CORRECT

logger = logging.getLogger(__name__)



@login_required
def studentsubmit(request):
    """Handle assignment submission"""
    user = request.user
    userassignmentbinding_ids = request.POST.getlist('userassignmentbinding_ids')
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
def teachercollect(request, course_id):
    """Handle assignment collection"""
    user = request.user
    logger.debug("user %s, method: %s" % (user, request.method))
    assignment_ids = request.POST.getlist('assignment_ids')
    userassignmentbinding_ids = request.POST.getlist('userassignmentbinding_ids')
    try:
        course = Course.objects.get(id = course_id)
        assert len(list(UserCourseBinding.objects.filter(user = user, course = course, is_teacher = True))) > 0, "%s is not a teacher of course %s" % (user, course)
        table_collect_mass = T_COLLECT_ASSIGNMENT(course.collectableassignments())
        RequestConfig(request).configure(table_collect_mass)
        table_collect_personal = T_COLLECT_UABINDING(course.collectableassignments_2())
        RequestConfig(request).configure(table_collect_personal)
    except Exception as e:
        logger.error("Invalid request with course id %s and user %s -- %s" % (course_id, user, e))
        return redirect('indexpage')
    if request.method == 'GET':
        context_dict = {
            'submenu': 'collect',
            'course': course,
            't_collect_mass': table_collect_mass,
            't_collect_personal': table_collect_personal,
        }
        return render(request, 'edu/assignments.html', context = context_dict) #FIXME: rename template new_assignment.html
    elif request.method == 'POST':
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
        for binding_id in userassignmentbinding_ids:
            try:
                binding = UserAssignmentBinding.objects.get(id = binding_id)
                assignment = binding.assignment
                assert assignment.course == course, "course mismatch"
                UserCourseBinding.objects.get(user = user, course = course, flag = assignment.flag, is_teacher = True)
                binding.do_collect()
                messages.info(request, 'Assignment %s of %s for course %s and flag %s is collected' % (assignment.name, binding.user, assignment.course.courseid, assignment.flag))
            except Exception as e:
                logger.error(e)
                messages.error(request, 'Cannot mark assignment collected -- %s' % e)
        url_next = reverse('assignment:collect', kwargs = {'course_id': course_id})
        pager = request.POST.get('pager')
        return redirect(url_next + "?%s" % pager) if pager else redirect('assignment:collect', course_id)
    else:
        return redirect('indexpage')


@login_required
def feedback_handler(request, course_id):
    """Mark assignments to correct"""
    from hub.models.assignment import ST_LOOKUP
    user = request.user
    logger.debug("user %s, method: %s" % (user, request.method))
    try:
        course = Course.objects.get(id = course_id)
        assert len(list(UserCourseBinding.objects.filter(user = user, course = course, is_teacher = True))) > 0, "%s is not a teacher of course %s" % (user, course)
    except Exception as e:
        logger.error("Invalid request with course id %s and user %s -- %s" % (course_id, user, e))
        return redirect('indexpage')
    if request.method == 'GET':
        extra = {}
        for k in [ 'state', 'name', 'user' ]:
            v = request.GET.get(k)
            if v:
                extra[k] = v
        table_feedback = T_CORRECT(course.lookup_userassignmentbindings(**extra))
        RequestConfig(request).configure(table_feedback)
        context_dict = {
            'submenu': 'feedback',
            'course': course,
            't_feedback': table_feedback,
            'states': ST_LOOKUP,
        }
        return render(request, 'edu/assignments.html', context = context_dict) #FIXME: rename template new_assignment.html
    elif request.method == 'POST':
        for k, v in request.POST.items():
            if not k.startswith('task_'):
                continue
            try:
                _, binding_id = k.split('_')
                if not v in [ 'correct', 'ready', 'reassign' ]:
                    continue
                score = request.POST.get('score_%s' % binding_id).strip()
                feedback_text = request.POST.get('feedback_text_%s' % binding_id).strip()

                binding = UserAssignmentBinding.objects.get(id = binding_id)
                UserCourseBinding.objects.get(user = user, course = binding.assignment.course, flag = binding.assignment.flag, is_teacher = True)
                if v == 'correct':
                    binding.state = UserAssignmentBinding.ST_CORRECTING
                    binding.corrector = user
                elif v == 'ready':
                    binding.state = UserAssignmentBinding.ST_FEEDBACK
                    binding.corrected_at = now()
                elif v == 'reassign': 
                    binding.state = UserAssignmentBinding.ST_WORKINPROGRESS
                    binding.corrected_at = now()
                try:
                    binding.score = float(score)
                except:
                    if len(score):
                        messages.warning(request, "The score must be a float")
                if len(feedback_text):
                    binding.feedback_text = feedback_text
                binding.save()
                messages.info(request, '%s\'s assignment %s for course %s and flag %s is marked corrected' % (binding.user.username, binding.assignment.name, binding.assignment.course.courseid, binding.assignment.flag))
            except Exception as e:
                logger.error(e)
                messages.error(request, 'Cannot mark assignment corrected -- %s' % e)
        url_next = reverse('assignment:feedback', kwargs = {'course_id': course_id})
        pager = request.POST.get('pager')
        return redirect(url_next + "?%s" % pager) if pager else redirect('assignment:feedback', course_id)
    else:
        return redirect('indexpage')


@login_required
def bind(request, course_id):
    from django.contrib.auth.models import User
    """Bind assignment and user"""
    user = request.user
    logger.debug("user %s, method: %s" % (user, request.method))
    try:
        course = Course.objects.get(id = course_id)
        assert len(list(UserCourseBinding.objects.filter(user = user, course = course, is_teacher = True))) > 0, "%s is not a teacher of course %s" % (user, course)
        table_bind = T_BIND(course.bindableassignments())
        RequestConfig(request).configure(table_bind)
    except Exception as e:
        logger.error("Invalid request with course id %s and user %s -- %s" % (course_id, user, e))
        return redirect('indexpage')
    if request.method == 'GET':
        context_dict = {
            'submenu': 'bind',
            'course': course,
            't_bind': table_bind,
        }
        return render(request, 'edu/assignments.html', context = context_dict) #FIXME: rename template new_assignment.html
    elif request.method == 'POST':
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
            if valid_from and valid_from > thetime:
                UserAssignmentBinding.objects.create(user = student, assignment = assignment, valid_from = valid_from, expires_at = expires_at, state = UserAssignmentBinding.ST_QUEUED)
            else:
                UserAssignmentBinding.objects.create(user = student, assignment = assignment, valid_from = valid_from, expires_at = expires_at)
    #FIXME> expiry check in model init!
            messages.info(request, "Creating an assignment %s for student %s" % (assignment.name, student))
        url_next = reverse('assignment:bind', kwargs = {'course_id': course_id})
        pager = request.POST.get('pager')
        logger.debug("next: %s %s" % (url_next, pager)) 
        return redirect(url_next + "?%s" % pager) if pager else redirect('assignment:bind', course_id)
    else:
        return redirect('indexpage')
    
@login_required
def search(request):
    course_id = request.POST.get('course_id')
    user = request.user
    extra = []
    for k in [ 'state', 'name', 'user' ]:
        v = request.POST.get(k)
        if v:
            extra.append("%s=%s" % (k, v))
    url_next = reverse('assignment:feedback', kwargs = {'course_id': course_id})
       # pager = request.POST.get('pager')
    return redirect(url_next + "?%s" % "&".join(extra)) if len(extra) else redirect('assignment:feedback', course_id)


#@login_required
#def update(request):
#    """Update assignment"""

urlpatterns = [
    url(r'(?P<course_id>\d+)/bind$', bind, name = 'bind'),
    url(r'(?P<course_id>\d+)/collect$', teachercollect, name = 'collect'),
    url(r'(?P<course_id>\d+)/feedback$', feedback_handler, name = 'feedback'),
    url(r'submit/?$', studentsubmit, name = 'submit'),
    url(r'search$', search, name = 'search'),
]


