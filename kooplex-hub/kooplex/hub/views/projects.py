from django.conf.urls import patterns, url, include
from django.shortcuts import render
from django.http import HttpRequest
from django.template import RequestContext
from datetime import datetime

from kooplex.lib.gitlab import Gitlab

def index(request):
    """Renders the projects page"""
    assert isinstance(request, HttpRequest)

    g = Gitlab()
    p = g.get_projects()

    return render(
        request,
        'projects/index.html',
        context_instance = RequestContext(request,
        {
            'title':'Projects',
            'message':'',
            'projects': p,
        })
    )

urlpatterns = [
    url(r'^$', index),
    #url(r'^/contact$', contact, name='contact'),
    #url(r'^/about', about, name='about'),
]