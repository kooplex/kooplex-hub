import re
import logging

from django.conf.urls import url
from django.shortcuts import redirect
from django.contrib.auth.models import User
from django.contrib.auth import login

from hub.models import Profile


logger = logging.getLogger(__name__)

def adduser(request, username):
    """"""
    assert not request.user.is_authenticated, "Logout before the call"
    try:
        u = User.objects.get(username = username)
    except User.DoesNotExist:
        logger.debug('NEW MOCK USER')
        u = User.objects.create(username = username, first_name = 'MOCK_%s' % username)
    login(request, u, backend = 'django.contrib.auth.backends.ModelBackend')
    return redirect('indexpage')


def removeuser(request, username):
    """"""
    assert request.user.username == username, "Login before you kill yourself"
    request.user.delete()
    logger.debug('MOCK USERDEL %s' % username)
    return redirect('indexpage')

urlpatterns = [
    url(r'loginas/(?P<username>\w+)$', adduser, name = 'addandlogin'),
    url(r'remove/(?P<username>\w+)$', removeuser, name = 'remove'),
]
