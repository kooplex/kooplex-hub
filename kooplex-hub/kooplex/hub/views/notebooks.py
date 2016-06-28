from django.conf.urls import patterns, url, include
from django.shortcuts import render
from django.http import HttpRequest
from django.template import RequestContext
from datetime import datetime

from kooplex.lib.gitlab import Gitlab
from kooplex.lib.spawner import Spawner

def notebooks(request):
    """Renders the notebooks page"""
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

urlpatterns = [
    url(r'^$', notebooks, name='notebooks'),
]