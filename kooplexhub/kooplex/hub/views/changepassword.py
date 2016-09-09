from django.conf.urls import patterns, url, include
from django.shortcuts import render
from django.http import HttpRequest
from django.template import RequestContext
from datetime import datetime
from django.contrib.auth.models import User
from django.contrib.auth import password_validation
from kooplex.lib.ldap import Ldap

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

    user = User.objects.get(username=username)
    if user.password != oldpassword:
        raise ValidationError("Password doesn't match!")
    else:
        l = Ldap()
        user.password = newpassword
        user = l.modify_user(user)
        user.save()

    return HttpResponseRedirect(HUB_URL)

urlpatterns = [
    url(r'^pform', change_password_form, name='pform'),
    url(r'^$', change_password, name='changepassword'),

]