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
    return render(request, 'edu/teaching.html')


@login_required
def courses(request):
    """Renders the projectlist page for students."""
    def f(binding):
        return binding.state in [ UserAssignmentBinding.ST_WORKINPROGRESS, UserAssignmentBinding.ST_SUBMITTED ]
    logger.debug('Rendering courses.html')
    bindings = filter(f, UserAssignmentBinding.objects.filter(user = request.user))
    table_submit = T_SUBMIT(bindings) 
    RequestConfig(request).configure(table_submit)
    context_dict = {
        't_submit': table_submit,
    }
    return render(request, 'edu/courses.html', context = context_dict)


urlpatterns = [
    url(r'teaching/?$', teaching, name = 'teaching'),
    url(r'courses/?$', courses, name = 'courses'),
]
