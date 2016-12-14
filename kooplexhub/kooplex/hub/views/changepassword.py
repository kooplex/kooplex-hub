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


HUB_URL = '/hub'


def change_password(request):
    """Renders the Change password page."""
    assert isinstance(request, HttpRequest)
    return render(
        request,
        'app/password-form.html',
        context_instance = RequestContext(request,
        {
            'title':'Change Password',
            'next_page': '/hub',
        })
    )

def change_password_form(request):
    """Checks password in ldap and changes it"""
    assert isinstance(request, HttpRequest)
    username = request.POST['username']
    oldpassword = request.POST['oldpassword']
    newpassword = request.POST['newpassword']
    gadmin = GitlabAdmin(request)
    userid = request.user.id
    try:
        msg = gadmin.modify_user(userid, 'password', newpassword)
    except ValidationError:
        return render(
            request,
            'app/password-form.html',
            context_instance=RequestContext(request,
            {
            'errors' : True,
            'title': 'Change Password',
            'next_page': '/hub',
        })
        )

    return HttpResponseRedirect(HUB_URL)

def change_password_form_ldap(request):
    """Checks password in ldap and changes it"""
    assert isinstance(request, HttpRequest)
    username = request.POST['username']
    oldpassword = request.POST['oldpassword']
    newpassword = request.POST['newpassword']

    l = Ldap()
    uu=request.user
    #print(uu.password)
    uu.set_password(newpassword)
    try:
        l.changepassword(request.user,oldpassword,newpassword)
        #l.modify_user(uu)
    except ValidationError:
        #print(oldpassword)
        return render(
            request,
            'app/password-form.html',
            context_instance=RequestContext(request,
            {
            'errors' : True,
            'title': 'Change Password',
            'next_page': '/hub',
        })
        )

    return HttpResponseRedirect(HUB_URL)

urlpatterns = [
    url(r'^$', change_password, name='changepassword'),
    url(r'^/pform', change_password_form, name='pform'),
    #

]