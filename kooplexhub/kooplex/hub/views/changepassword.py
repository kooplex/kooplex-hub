from django.conf.urls import patterns, url, include
from django.shortcuts import render
from django.http import HttpRequest
from django.template import RequestContext
from datetime import datetime
from django.contrib.auth.models import User
from kooplex.lib.ldap import Ldap
from django.http import HttpRequest, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.core.exceptions import ValidationError
from kooplex.lib.gitlabadmin import GitlabAdmin
from kooplex.lib.debug import *
from kooplex.lib.libbase import get_settings
import os

HUB_URL = '/hub'

def change_password(request):
    """Renders the Change password page."""
    assert isinstance(request, HttpRequest)
    user = request.user
    return render(
        request,
        'app/password-form.html',
        context_instance = RequestContext(request,
        {
            'user': user,
            'next_page': HUB_URL,
        })
    )

def change_password_form_ldap(request):
    """Checks password in ldap and changes it"""
    assert isinstance(request, HttpRequest)
    username = request.POST['username']
    try:
        oldpassword = request.POST['oldpassword']
        newpassword = request.POST['newpassword']
        newpassword2 = request.POST['newpassword2']
        assert len(oldpassword), "Don't forget to type your old password"
        assert len(newpassword), "Don't forget to type your new password"
        assert newpassword == newpassword2, "Make sure you type your new password twice the same"

        l = Ldap()
        uu = request.user
        uu.set_password(newpassword)            #FIXME: should not be here
        l.changepassword(request.user, oldpassword, newpassword)

#FIXME: dirty
        srv_dir = get_settings('users', 'srv_dir', None, '')
        home_dir = get_settings('users', 'home_dir', None, '')
        home_dir = os.path.join(srv_dir, home_dir.replace('{$username}', request.user.username))
        davfs_dir = os.path.join(home_dir, '.davfs2')
        davsecret_fn = os.path.join(davfs_dir, "secrets")
        with open(davsecret_fn, "w") as f:
            f.write("http://kooplex-nginx/ownCloud/remote.php/webdav/ %s %s" % (request.user.username, newpassword))
##############


    except Exception as e:
        return render(
            request,
            'app/password-form.html',
            context_instance=RequestContext(request,
            {
            'errors' : str(e),
            'title': 'Change Password',
            'next_page': HUB_URL,
        })
        )

    return HttpResponseRedirect(HUB_URL)

urlpatterns = [
    url(r'^$', change_password, name = 'changepassword'),
    url(r'^pform', change_password_form_ldap, name = 'pform'),
]

