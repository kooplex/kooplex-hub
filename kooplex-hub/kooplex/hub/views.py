"""
Definition of views.
"""

from django.shortcuts import render
from django.http import HttpRequest
from django.template import RequestContext
from datetime import datetime

from kooplex.lib.gitlab import Gitlab
from kooplex.lib.spawner import Spawner

def home(request):
    """Renders the home page."""
    assert isinstance(request, HttpRequest)
    return render(
        request,
        'app/index.html',
        context_instance = RequestContext(request,
        {
            'title':'Home Page',
            'year':datetime.now().year,
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

def projects(request):
    """Renders the projects page"""
    assert isinstance(request, HttpRequest)

    g = Gitlab()
    p = g.get_projects()

    return render(
        request,
        'app/projects.html',
        context_instance = RequestContext(request,
        {
            'title':'Projects',
            'message':'',
            'projects': p,
        })
    )

def containers(request):
    """Renders the containers page"""
    assert isinstance(request, HttpRequest)

    s = Spawner(request.user.username)
    c = s.list_containers()

    return render(
        request,
        'app/containers.html',
        context_instance = RequestContext(request,
        {
            'title':'Running containers',
            'message':'',
            'containers': c,
        })
    )

def spawn(request):
    """Renders the containers page"""
    assert isinstance(request, HttpRequest)

    s = Spawner(request.user.username)
    c = [ s.spawn_container('debian:jessie', '4', '/bin/bash', 8111) ]
         
    return render(
        request,
        'app/containers.html',
        context_instance = RequestContext(request,
        {
            'title':'Running containers',
            'message':'',
            'containers': None,
        })
    )