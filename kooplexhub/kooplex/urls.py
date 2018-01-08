"""
Definition of urls for kooplex.
"""

from datetime import datetime
import django
import django.contrib.auth
from django.contrib.auth.views import logout
from django.contrib.auth.views import login
from django.contrib import admin
from django.conf.urls import patterns, url, include
from django.conf import settings


import kooplex
import kooplex.hub
from kooplex.hub.forms import BootstrapAuthenticationForm, BootstrapPasswordChangeForm
from kooplex.hub.views import home
from kooplex.hub.views import changepassword

from django.contrib.auth.forms import PasswordChangeForm

from django.shortcuts import render, redirect
from django.template import RequestContext


# Uncomment the next lines to enable the admin:
from django.conf.urls import include
from django.contrib import admin
admin.autodiscover()

import os
from kooplex.lib.libbase import get_settings

from kooplex.hub.models.user import HubUser
import pwgen
from kooplex.lib.sendemail import send_token
from django.contrib.auth.models import User
from kooplex.lib.ldap import Ldap

def hw(request):
    from django.http import HttpResponse
    return HttpResponse('Szia')

def pwreset(request):
    return render(
        request,
        'app/password-reset.html',
        context_instance = RequestContext(request,
        {
        })
    )

def preset(request):
    username = request.POST['username']
    email = request.POST['email']
    try:
        assert len(username), 'Please provide a username'
        hubuser = HubUser.objects.get(username = username)
        assert hubuser.email == email, 'Wrong e-mail address is provided'
        token = pwgen.pwgen(12)
        with open('/tmp/%s.token'%hubuser.username, 'w') as f:
            f.write(token)
        send_token(hubuser, token)
    except Exception as e:
        return render(
            request,
            'app/password-reset.html',
            context_instance = RequestContext(request,
            {
               'errors': str(e),
            })
        )
    return render(
        request,
        'app/password-reset-2.html',
        context_instance = RequestContext(request,
        {
           'username': username,
        })
    )

def preset2(request):
    username = request.POST['username']
    token = request.POST['token']
    password1 = request.POST['password1']
    password2 = request.POST['password2']
    try:
#        hubuser = HubUser.objects.get(username = username)
        assert len(token), 'Please check your e-mail for the token and type it'
        assert len(password1), 'You cannot have an empty password'
        tokengood = open('/tmp/%s.token'%username).read()
        assert token == tokengood, 'You provide an invalid token'
        assert password1 == password2, 'Your passwords do not match'
        l = Ldap()
        dj_user = HubUser.objects.get(username = username)
        l.changepassword(dj_user, 'doesntmatter', password1, validate_old_password = False)

        home_dir = os.path.join(get_settings('volumes', "home"), username)
        davfs_dir = os.path.join(home_dir, '.davfs2')

        ## preapare davfs secret file
        davsecret_fn = os.path.join(davfs_dir, "secrets")
        with open(davsecret_fn, "w") as f:
            f.write("http://kooplex-nginx/ownCloud/remote.php/webdav/ %s %s" % (username, password1))
        os.chown(davsecret_fn, dj_user.uid, dj_user.gid)
        os.chmod(davsecret_fn, 0b110000000)

    except Exception as e:
        return render(
            request,
            'app/password-reset-2.html',
            context_instance = RequestContext(request,
            {
               'errors': str(e),
               'username': username
            })
        )
    return redirect('/hub/login/')

urlpatterns = [
    url(r'^hub/login/$',
        django.contrib.auth.views.login,
        {
            'template_name': 'app/login.html',
            'authentication_form': BootstrapAuthenticationForm,
            'extra_context':
            {
                'next_page': '/hub/notebooks',
                'year' : 2018,
                'hubuser' : None,
                'title' : 'Login',
            }
        },
        name='login'),

     url(r'hub/login/passwordreset$', pwreset, {}, name = 'pwreset'),
     url(r'hub/login/preset$', preset, {}, name = 'preset'),
     url(r'hub/login/preset2$', preset2, {}, name = 'preset2'),
    url(r'^hub/logout$',
        django.contrib.auth.views.logout,
        {
            'next_page': '/hub',
        },
        name='logout'),

    # Uncomment the admin/doc line below to enable admin documentation:
    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
    url(r'^admin/', include('kooplex.hub.admin')),



    # AllAuth
    # url(r'^accounts/', include('allauth.urls')),

    # OAuth2 provider
    # url(r'^oauth2/', include('oauth2_provider.urls', namespace='oauth2_provider')),

    url(r'^hub/', include('kooplex.hub.urls')),
    
    #url(r'^pform',include('kooplex.hub.views.changepassword')),
    #url(r'^changepassword/', include('kooplex.hub.views.changepassword')),
    #url(r'^changepassword', changepassword.change_password),
    
]
