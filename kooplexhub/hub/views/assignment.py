import re
import logging

from django.conf.urls import url
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import redirect

from hub.models import Course, UserCourseBinding, Assignment

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
        messages.error(request, 'Cannot start the container -- %s' % e)
    messages.info(request, 'Assignments are registered for course %s and flag %s' % (course.courseid, ", ".join(course_flags)))
    return redirect('teaching:list')


urlpatterns = [
    url(r'new/?$', new, name = 'new'),
]
