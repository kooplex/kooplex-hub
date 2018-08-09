import logging
import pwgen

from django.conf.urls import url
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from hub.forms import FormBiography

logger = logging.getLogger(__name__)

@login_required
def updateprofile(request):
    logger.debug("user %s" % request.user)
    next_page = request.POST.get('next_page', 'indexpage') #FIXME
    user_id = request.POST.get('user_id')
    if user_id is not None and int(user_id) == request.user.id:
        form = FormBiography(request.POST, instance = request.user.profile)
        form.save()
        messages.info(request, 'Your profile is updated')
    else:
        logger.error("user id mismatch: %s tries to save %s %s" % (request.user, request.user.id, request.POST.get('user_id')))
        messages.error(request, 'Profile update is refused.')
    return redirect(next_page)

@login_required
def changetoken(request):
    logger.debug("user %s" % request.user)
    next_page = request.POST.get('next_page', 'indexpage') #FIXME
    profile = request.user.profile
    profile.token = pwgen.pwgen(64)
    profile.save()
    messages.warning(request, 'Your secret token is updated. You will not be able to access your running containers until you restart them.')
    return redirect(next_page)

urlpatterns = [
    url(r'^profile/?$', updateprofile, name = 'updateprofile'),
    url(r'^token/?$', changetoken, name = 'changetoken'),
]

