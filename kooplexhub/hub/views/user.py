import logging
import pwgen

from django.conf.urls import url
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages

logger = logging.getLogger(__name__)

@login_required
def updateprofile(request):
    logger.debug("user %s" % request.user)
    next_page = request.POST.get('next_page', 'indexpage') #FIXME
    bio = request.POST.get('bio')
    location = request.POST.get('location')
    profile = request.user.profile
    profile.bio = bio
    profile.location = location
    profile.save()
    messages.info(request, 'Your profile is updated')
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

