import logging

from django.db import transaction
from django.conf.urls import url
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import redirect, render
from django_tables2 import RequestConfig

from hub.models import CourseCode, Course, UserCourseCodeBinding, UserCourseBinding
from hub.models import Assignment
from kooplex.lib import now, translate_date
from hub.forms import FormAssignment

logger = logging.getLogger(__name__)


@login_required
def teaching(request):
    """Renders the projectlist page for courses taught."""
    logger.debug('Rendering teaching.html')
    context_dict = {
        'menu_teaching': 'active',
        'next_page': 'education:teaching', 
    }
    return render(request, 'edu/teaching.html', context = context_dict)


@login_required
def courses(request):
    """Renders the projectlist page for students."""
    logger.debug('Rendering courses.html')
    context_dict = {
        'menu_teaching': 'active',
        'next_page': 'education:courses', 
    }
    return render(request, 'edu/courses.html', context = context_dict)


@login_required
def conf_meta(request, course_id, next_page):
    raise NotImplementedError


@login_required
def newassignment(request, course_id):
    """Renders assignment management form."""
    user = request.user
    logger.debug("user %s, method: %s" % (user, request.method))
    try:
        course = Course.objects.get(id = course_id)
        binding = UserCourseBinding.objects.get(user = user, course = course, is_teacher = True)
    except Course.DoesNotExist:
        logger.error("Missing course id %s and user %s" % (course_id, user))
        return redirect('education:teaching')
    except UserCourseBinding.DoesNotExist:
        logger.error("Missing course id %s and user %s" % (course_id, user))
        messages.error(request, 'You are not allowed to create an assignment for %s' % (course))
        return redirect('education:teaching')
    if request.method == 'GET':
        context_dict = {
            'menu_teaching': 'active',
            'submenu': 'new',
            'course': course,
            'f_assignment': FormAssignment(user = user, course = course),
            'next_page': 'education:teaching',
        }
        return render(request, 'edu/assignments.html', context = context_dict)
    elif request.method == 'POST':
        coursecode_ids = request.POST.getlist("coursecodes")
        name = request.POST.get("name").strip()
        description = request.POST.get("description").strip()
        folder = request.POST.get("folder")
        timenow = now()
        valid_from = translate_date(request.POST.get('valid_from')) or timenow
        expires_at = translate_date(request.POST.get('expires_at'))
        is_massassignment = bool(request.POST.get("is_massassignment"))
        can_studentsubmit = bool(request.POST.get("can_studentsubmit"))
        remove_collected = bool(request.POST.get("remove_collected"))
        try:
            assert valid_from >= timenow, "You try to chedule assignment behind time."
            assert len(name), "You need to provide a name"
            assert len(coursecode_ids), "You need to select at least one course code"
            extra = {}
            if expires_at:
                assert (expires_at - valid_from).total_seconds() >= 60, "Expiry is too close to handout. "
            for coursecodeid in coursecode_ids:
                coursecode = CourseCode.objects.get(id = coursecodeid)
                assert coursecode.course == course, "Course code missmatch"
                UserCourseCodeBinding.objects.get(coursecode = coursecode, user = user, is_teacher = True)
                logger.debug("coursecode id %s" % coursecodeid)
                with transaction.atomic():
                    assignments = Assignment.objects.filter(
                        coursecode = coursecode, 
                        name = name, 
                        creator = user, 
                        description = description, 
                        folder = folder, 
                        can_studentsubmit = can_studentsubmit, 
                        remove_collected = remove_collected,
                        is_massassignment = is_massassignment, 
                        expires_at = expires_at
                        )
                    if len(assignments):
                        logger.warning('Prevented from duplicating assignments for course code %s' % (coursecode))
                        messages.warning(request, 'Maybe you double clicked on assignments.')
                        continue
                    Assignment.objects.create(
                        coursecode = coursecode, 
                        name = name, 
                        creator = user, 
                        description = description, 
                        folder = folder, 
                        can_studentsubmit = can_studentsubmit, 
                        remove_collected = remove_collected,
                        is_massassignment = is_massassignment, 
                        valid_from = valid_from,
                        expires_at = expires_at
                    )
                    logger.info('New assignments for course code %s' % (coursecode))
                    messages.info(request, 'New assignments for course code %s' % (coursecode))
        except Exception as e:
            raise
            logger.error(e)
            messages.error(request, 'Cannot fully register assignment -- %s' % e)
            return redirect('education:newassignment', course.id)
    return redirect('indexpage')



urlpatterns = [
    url(r'^teaching/?$', teaching, name = 'teaching'),
    url(r'^courses/?$', courses, name = 'courses'),
    url(r'^configurecourse/(?P<course_id>\d+)/meta/(?P<next_page>\w+:?\w*)$', conf_meta, name = 'conf_meta'), 
    url(r'^newassignemnt/(?P<course_id>\d+)$', newassignment, name = 'newassignment'),
]
