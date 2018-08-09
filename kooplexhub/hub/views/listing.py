import logging

from django.conf.urls import url
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

logger = logging.getLogger(__name__)


@login_required
def teaching(request):
    """Renders the projectlist page."""
    logger.debug('Rendering teaching.html')
    return render(request, 'edu/teaching.html')


@login_required
def courses(request):
    """Renders the projectlist page."""
    logger.debug('Rendering courses.html')
    return render(request, 'edu/courses.html')


urlpatterns = [
    url(r'teaching/?$', teaching, name = 'teaching'),
    url(r'courses/?$', courses, name = 'courses'),
]
