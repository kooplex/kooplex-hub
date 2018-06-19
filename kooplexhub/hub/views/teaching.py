import re
import logging

from django.conf.urls import url
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from hub.models import Image

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
    return render(request, 'project/teaching.html', context = context_dict)


def bla(request):
    pass

urlpatterns = [
    url(r'list/?$', show, name = 'list'),
]
