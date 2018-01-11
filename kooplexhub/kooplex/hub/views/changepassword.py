from django.template import RequestContext
from django.conf.urls import url, include
from django.shortcuts import render, redirect
from django.http import HttpRequest

def passwordchange(request):
    """Renders the password change page."""
    assert isinstance(request, HttpRequest)
    pass

def passwordreset(request):
    """Renders the password reset request page."""
    assert isinstance(request, HttpRequest)
    return render(
        request,
        'auth/passwordreset.html',
        context_instance = RequestContext(request, {})
    )

def passwordresettoken(request):
    """Renders the password reset token input form."""
    assert isinstance(request, HttpRequest)
    pass
## ##    username = request.POST['username']
## ##    email = request.POST['email']
## ##    try:
## ##        assert len(username), 'Please provide a username'
## ##        hubuser = HubUser.objects.get(username = username)
## ##        assert hubuser.email == email, 'Wrong e-mail address is provided'
## ##        token = pwgen.pwgen(12)
## ##        with open('/tmp/%s.token'%hubuser.username, 'w') as f:
## ##            f.write(token)
## ##        send_token(hubuser, token)
## ##    except Exception as e:
## ##        return render(
## ##            request,
## ##            'app/password-reset.html',
## ##            context_instance = RequestContext(request,
## ##            {
## ##               'errors': str(e),
## ##            })
## ##        )
## ##    return render(
## ##        request,
## ##        'app/password-reset-2.html',
## ##        context_instance = RequestContext(request,
## ##        {
## ##           'username': username,
## ##        })
## ##    )

def passwordresetfinish(request):
    """Renders the set new password form."""
    assert isinstance(request, HttpRequest)
    pass
## ##    username = request.POST['username']
## ##    token = request.POST['token']
## ##    password1 = request.POST['password1']
## ##    password2 = request.POST['password2']
## ##    try:
## ###        hubuser = HubUser.objects.get(username = username)
## ##        assert len(token), 'Please check your e-mail for the token and type it'
## ##        assert len(password1), 'You cannot have an empty password'
## ##        tokengood = open('/tmp/%s.token'%username).read()
## ##        assert token == tokengood, 'You provide an invalid token'
## ##        assert password1 == password2, 'Your passwords do not match'
## ##        l = Ldap()
## ##        dj_user = HubUser.objects.get(username = username)
## ##        l.changepassword(dj_user, 'doesntmatter', password1, validate_old_password = False)
## ##
## ##        home_dir = os.path.join(get_settings('volumes', "home"), username)
## ##        davfs_dir = os.path.join(home_dir, '.davfs2')
## ##
## ##        ## preapare davfs secret file
## ##        davsecret_fn = os.path.join(davfs_dir, "secrets")
## ##        with open(davsecret_fn, "w") as f:
## ##            f.write(os.path.join(get_settings('owncloud', 'inner_url'), "remote.php/webdav/") + " %s %s" % (username, password1))
## ##        os.chown(davsecret_fn, dj_user.uid, dj_user.gid)
## ##        os.chmod(davsecret_fn, 0b110000000)
## ##
## ##    except Exception as e:
## ##        return render(
## ##            request,
## ##            'app/password-reset-2.html',
## ##            context_instance = RequestContext(request,
## ##            {
## ##               'errors': str(e),
## ##               'username': username
## ##            })
## ##        )
## ##    return redirect('/hub/login/')














##from django.conf.urls import patterns, url, include
##from django.shortcuts import render
##from django.http import HttpRequest
##from django.template import RequestContext
##from datetime import datetime
##from django.contrib.auth.models import User
##from kooplex.lib.ldap import Ldap
##from django.http import HttpRequest, HttpResponseRedirect
##from django.shortcuts import render_to_response
##from django.core.exceptions import ValidationError
##from kooplex.lib.gitlabadmin import GitlabAdmin
##from kooplex.lib.debug import *
##from kooplex.lib.libbase import get_settings, mkdir
##import os
##from kooplex.hub.models.user import User as HubUser #FIXME:
##
##HUB_URL = '/hub'
##
##def change_password(request):
##    """Renders the Change password page."""
##    assert isinstance(request, HttpRequest)
##    user = request.user
##    return render(
##        request,
##        'app/password-form.html',
##        context_instance = RequestContext(request,
##        {
##            'user': user,
##            'next_page': HUB_URL,
##        })
##    )
##
##def change_password_form_ldap(request):
##    """Checks password in ldap and changes it"""
##    assert isinstance(request, HttpRequest)
##    try:
##        oldpassword = request.POST['oldpassword']
##        newpassword = request.POST['newpassword']
##        newpassword2 = request.POST['newpassword2']
##        assert len(oldpassword), "Don't forget to type your old password"
##        assert len(newpassword), "Don't forget to type your new password"
##        assert newpassword == newpassword2, "Make sure you type your new password twice the same"
##
##        l = Ldap()
##        uu = request.user
##        uu.set_password(newpassword)            #FIXME: should not be here
##        l.changepassword(request.user, oldpassword, newpassword)
##
###FIXME: dirty
##        dj_user = HubUser.objects.get(username = request.user.username,)
##        home_dir = os.path.join(get_settings('volumes', 'home'), request.user.username)
##        davfs_dir = os.path.join(home_dir, '.davfs2')
##        mkdir(davfs_dir, uid=dj_user.uid, gid=dj_user.gid, mode=0b111000000)
##        davsecret_fn = os.path.join(davfs_dir, "secrets")
##        with open(davsecret_fn, "w") as f:
##            f.write(os.path.join(get_settings('owncloud', 'inner_url'), "remote.php/webdav/") + " %s %s" % (request.user.username, newpassword))
##        os.chown(davsecret_fn, dj_user.uid, dj_user.gid)
##        os.chmod(davsecret_fn, 0b110000000)
##
################
##
##    except Exception as e:
##        return render(
##            request,
##            'app/password-form.html',
##            context_instance=RequestContext(request,
##            {
##            'errors' : str(e),
##            'title': 'Change Password',
##            'next_page': HUB_URL,
##        })
##        )
##
##    return HttpResponseRedirect(HUB_URL)
##
##urlpatterns = [
##    url(r'^$', change_password, name = 'changepassword'),
##    url(r'^pform', change_password_form_ldap, name = 'pform'),
##]
##
