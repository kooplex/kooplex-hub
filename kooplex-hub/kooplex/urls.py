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
from kooplex.hub.forms import BootstrapAuthenticationForm
from kooplex.hub.views import home

# Uncomment the next lines to enable the admin:
# from django.conf.urls import include
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = (
    # Examples:
    url(r'^$', kooplex.hub.views.home, name='home'),
    url(r'^contact$', kooplex.hub.views.contact, name='contact'),
    url(r'^about', kooplex.hub.views.about, name='about'),
    url(r'^login/$',
        django.contrib.auth.views.login,
        {
            'template_name': 'app/login.html',
            'authentication_form': BootstrapAuthenticationForm,
            'extra_context':
            {
                'title':'Log in',
                'year':datetime.now().year,
            }
        },
        name='login'),
    url(r'^logout$',
        django.contrib.auth.views.logout,
        {
            'next_page': '/',
        },
        name='logout'),

    # Uncomment the admin/doc line below to enable admin documentation:
    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),

    # AllAuth
    # url(r'^accounts/', include('allauth.urls')),

    # OAuth2 provider
    # url(r'^oauth2/', include('oauth2_provider.urls', namespace='oauth2_provider')),

    url(r'^projects', kooplex.hub.views.projects, name='projects'),
    url(r'^containers', kooplex.hub.views.containers, name='containers'),
    url(r'^spawn', kooplex.hub.views.spawn, name='spawn'),
)
