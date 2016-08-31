from django.conf.urls import patterns, url, include
from django.shortcuts import render
from django.http import HttpRequest
from django.template import RequestContext
from datetime import datetime

from kooplex.lib.gitlab import Gitlab
from kooplex.lib.spawner import Spawner

def worksheets(request):
    """Renders the worksheets page"""
    assert isinstance(request, HttpRequest)

    return render(
        request,
        'app/error.html',
        context_instance=RequestContext(request,
        {
            'error_title': 'This page is under construction',
        })
    )
#    return render(
#        request,
#        'app/worksheets.html',
#        context_instance = RequestContext(request,
#        {
#            'title':'Browse worksheets',
#            'message':'',
#            'items': items,
#        })
#    )

urlpatterns = [
    url(r'^$', worksheets, name='worksheets'),
]