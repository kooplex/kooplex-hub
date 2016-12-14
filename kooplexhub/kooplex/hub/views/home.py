from django.conf.urls import patterns, url, include
from django.shortcuts import render
from django.http import HttpRequest
from django.template import RequestContext
from datetime import datetime

from kooplex.lib.gitlabadmin import GitlabAdmin

def index(request):
    """Renders the home page."""
    assert isinstance(request, HttpRequest)
    username = request.user.username
    gadmin = GitlabAdmin(request)
    print("U"+username)
    isadmin = gadmin.check_useradmin(username)
    return render(
        request,
        'app/index.html',
        context_instance = RequestContext(request,
        {
            'title':'Home Page',
            'year':datetime.now().year,
            'username': username,
            'admin': isadmin,
        })
    )

def contact(request):
    """Renders the contact page."""
    assert isinstance(request, HttpRequest)
    return render(
        request,
        'app/contact.html',
        context_instance = RequestContext(request,
        {
            'title':'Contact',
            'message':'Your contact page.',
            'year':datetime.now().year,
        })
    )


def about(request):
    """Renders the about page."""
    assert isinstance(request, HttpRequest)
    return render(
        request,
        'app/about.html',
        context_instance = RequestContext(request,
        {
            'title':'About',
            'message':'Your application description page.',
            'year':datetime.now().year,
        })
    )

urlpatterns = [
    url(r'^$', index, name='home'),
    url(r'^contact$', contact, name='contact'),
    url(r'^about', about, name='about'),
]