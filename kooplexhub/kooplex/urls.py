﻿"""
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

# Uncomment the next lines to enable the admin:
# from django.conf.urls import include
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = (
    url(r'^hub/login/$',
        django.contrib.auth.views.login,
        {
            'template_name': 'app/login.html',
            'authentication_form': BootstrapAuthenticationForm,
            'extra_context':
            {
                'title':'Log in',
                'year':datetime.now().year,
                'next_page': '/hub/notebooks',
            }
        },
        name='login'),
    url(r'^hub/chan/$',
        django.contrib.auth.views.password_change,
        {
            'template_name': 'app/change-password.html',
            'password_change_form': BootstrapPasswordChangeForm,
            'post_change_redirect': '/hub',
            'extra_context':
            {
                'title':'Change Password',
                'year':datetime.now().year,
                'next_page': '/hub',
            }
        },
        name='chan'),
    url(r'^hub/logout$',
        django.contrib.auth.views.logout,
        {
            'next_page': '/hub',
        },
        name='logout'),

    # Uncomment the admin/doc line below to enable admin documentation:
    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
#    url(r'^admin/', include(admin.site.urls)),
    url(r'^admin/', include('kooplex.hub.urls')),

    # AllAuth
    # url(r'^accounts/', include('allauth.urls')),

    # OAuth2 provider
    # url(r'^oauth2/', include('oauth2_provider.urls', namespace='oauth2_provider')),

    url(r'^hub/', include('kooplex.hub.urls')),
    
    #url(r'^pform',include('kooplex.hub.views.changepassword')),
    #url(r'^changepassword/', include('kooplex.hub.views.changepassword')),
    #url(r'^changepassword', changepassword.change_password),
    

)
