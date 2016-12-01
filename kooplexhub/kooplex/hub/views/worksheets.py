from django.conf.urls import patterns, url, include
from django.shortcuts import render
from django.http import HttpRequest
from django.template import RequestContext
from datetime import datetime

from kooplex.lib.gitlab import Gitlab
from kooplex.lib.spawner import Spawner
from kooplex.lib.dashboards import Dashboards
from kooplex.lib.debug import *
DEBUG = True


def worksheets(request):
    """Renders the worksheets page"""
    assert isinstance(request, HttpRequest)

#    return render(
#        request,
#        'app/error.html',
#        context_instance=RequestContext(request,
#        {
#            'error_title': 'This page is under construction',
#        })
#    )

    D = Dashboards()
    #list_of_dashboards = D.list_all()
    list_of_dashboards  = [{'path':'user/project_owner/project_name'},{'path':'user2/project_owner/project_name'}]
    
    return render(
        request,
        'app/worksheets.html',
        context_instance = RequestContext(request,
        {
            'title':'Browse worksheets',
            'message':'',
            'items': items,
            'dashboards': list_of_dashboards,
       })
    )

urlpatterns = [
    url(r'^$', worksheets, name='worksheets'),
]