import logging

from django.conf.urls import url
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django_tables2 import RequestConfig

from hub.models import Course, UserCourseBinding

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
            assert valid_from >= timenow, "You try to chedule assignment behind time."
            assert len(name), "You need to provide a name"
            assert len(course_flags), "You need to select at least one course flag"
            course = Course.objects.get(id = course.id)
            goodflags = set([ b.flag for b in UserCourseBinding.objects.filter(course = course, user = user, is_teacher = True) ])
            course_flags.intersection_update(goodflags)
            assert len(course_flags), "You are not authorized to save assignment to course flags provided"
            extra = {}
            if expires_at:
                assert (expires_at - valid_from).total_seconds() >= 60, "Expiry is too close to handout. "
            for flag in course_flags:
                logger.debug("flag %s" % flag)
                with transaction.atomic():
                    assignments = Assignment.objects.filter(
                        course = course, 
                        flag = flag, 
                        name = name, 
                        creator = user, 
                        description = description, 
                        folder = folder, 
                        can_studentsubmit = can_studentsubmit, 
                        is_massassignment = is_massassignment, 
                        expires_at = expires_at
                        )
                    if len(assignments):
                        logger.warning('Prevented from duplicating assignments for course %s and flag %s' % (course.courseid, flag))
                        messages.warning(request, 'Maybe you double clicked on assignments for course %s and flag %s' % (course.courseid, flag))
                        continue
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
                    logger.info('New assignments for course %s and flag %s' % (course.courseid, flag))
                    messages.info(request, 'New assignments for course %s and flag %s' % (course.courseid, flag))
        except Exception as e:
            logger.error(e)
            messages.error(request, 'Cannot fully register assignment -- %s' % e)
            return redirect('assignment:new', course.id)
    return redirect('indexpage')



urlpatterns = [
    url(r'^teaching/?$', teaching, name = 'teaching'),
    url(r'^courses/?$', courses, name = 'courses'),
    url(r'^configurecourse/(?P<course_id>\d+)/meta/(?P<next_page>\w+:?\w*)$', conf_meta, name = 'conf_meta'), 
    url(r'^newassignemnt/(?P<course_id>\d+)$', newassignment, name = 'newassignment'),
]
