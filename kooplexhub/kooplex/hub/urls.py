from django.contrib.auth.views import login, logout
from django.template import RequestContext
from django.conf.urls import url, include
from django.shortcuts import render, redirect
from django.http import HttpRequest, HttpResponseRedirect
from datetime import datetime

from kooplex.hub.forms import BootstrapAuthenticationForm
from kooplex.hub.views.changepassword import *

def indexpage(request):
    """Renders the home page."""
    assert isinstance(request, HttpRequest)
    if request.user.is_active:
        return redirect('/hub/projects')

    return render(
        request,
        'app/index.html',
        context_instance = RequestContext(request,
        {
            'title': 'Home Page',
            'year': datetime.now().year,
        })
    )

def tutorial(request):
    """Renders the page with videos."""
    assert isinstance(request, HttpRequest)
    return render(request, 'tutorial/tutorial.html')

login_kwargs = {
    'template_name': 'auth/login.html',
    'authentication_form': BootstrapAuthenticationForm,
    'extra_context':
    {
        'next_page': '/hub/projects',
        'year': datetime.now().year,
        'title' : 'Login',
    }
}

urlpatterns = [
    url(r'^/?$', indexpage, name = 'indexpage'),
    url(r'^/tutorial$', tutorial, name = 'tutorial'),
    url(r'^/login/?$', login, login_kwargs, name = 'login'),
    url(r'^/logout$', logout, { 'next_page': '/hub', }, name = 'logout'),

    url(r'^/passwordreset$', passwordreset, name = 'resetpassword'),
    url(r'^/passwordtoken$', passwordresettoken, name = 'passwordresettoken'),
    url(r'^/setnewpassword$', passwordresetfinish, name = 'setnewpassword'),
    url(r'^/changepassword', passwordchange, name = 'changepassword'),

    url(r'^/reports', include('kooplex.hub.views.reports')),
    url(r'^/projects', include('kooplex.hub.views.projects')),
]
