from django.shortcuts import render
from django.http import HttpRequest
from django.template import RequestContext
from datetime import datetime

from kooplex.lib.gitlab import Gitlab
from kooplex.lib.spawner import Spawner

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