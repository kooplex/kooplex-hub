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

logger = logging.getLogger(__name__)




    
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
    url(r'search$', search, name = 'search'),
]


