import logging

from django.conf.urls import url
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django_tables2 import RequestConfig

from hub.forms import T_SUBMIT
from hub.models import UserAssignmentBinding

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
    bindings = UserAssignmentBinding.objects.filter(user = request.user)
    table_submit = T_SUBMIT(bindings) 
    RequestConfig(request).configure(table_submit)
    context_dict = {
        'menu_teaching': 'active',
        'next_page': 'education:courses', 
        't_submit': table_submit,
    }
    return render(request, 'edu/courses.html', context = context_dict)


@login_required
def conf_meta(request, course_id, next_page):
    raise NotImplementedError

urlpatterns = [
    url(r'^teaching/?$', teaching, name = 'teaching'),
    url(r'^courses/?$', courses, name = 'courses'),
    url(r'^configurecourse/(?P<course_id>\d+)/meta/(?P<next_page>\w+:?\w*)$', conf_meta, name = 'conf_meta'), 
]
