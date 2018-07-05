import re
import logging

from django.conf.urls import url
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from hub.models import Image, Project

logger = logging.getLogger(__name__)

@login_required
def show(request):
    """Renders the projectlist page."""
    user = request.user
    logger.debug('Rendering teaching.html')
    context_dict = {
        'user': user,
        'images': Image.objects.all(),
    }
    return render(request, 'edu/teaching.html', context = context_dict)


@login_required
def assignmentform(request, project_id):
    """Renders assignment management form."""
    from hub.models import UserCourseBinding
    user = request.user
    logger.debug('Rendering assignments.html')
    try:
        project = Project.objects.get(id = project_id)
        assert len(list(UserCourseBinding.objects.filter(user = user, course = project.course, is_teacher = True))) > 0, "%s is not a teacher of course %s" % (user, project.course)
    except Exception as e:
        logger.error("Invalid request with project id %s and user %s -- %s" % (project_id, user, e))
        return redirect('indexpage')
    context_dict = {
        'user': user,
        'project': project,
    }
    return render(request, 'edu/assignments.html', context = context_dict)

urlpatterns = [
    url(r'list/?$', show, name = 'list'),
    url(r'assignment/(?P<project_id>\d+)$', assignmentform, name = 'assignment'),
]
