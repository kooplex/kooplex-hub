from django.conf.urls import patterns, url, include
from django.shortcuts import render
from django.http import HttpRequest
from django.template import RequestContext
from datetime import datetime
from django.http import HttpRequest, HttpResponseRedirect


from kooplex.lib.libbase import get_settings
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
    #base_url = get_settings('dashboards', 'base_url', None, '')
    dashboard_url="http://polc.elte.hu:3000"
    D = Dashboards()
    list_of_dashboards = D.list_dashboards(request)
 #   list_of_dashboards  = [{'path':'user/project_owner/project_name'},{'path':'user2/project_owner/project_name'}]
    
    return render(
        request,
        'app/worksheets.html',
        context_instance = RequestContext(request,
        {
            'title':'Browse worksheets',
            'message':'',
            'dashboard_url': dashboard_url,
            'dashboards': list_of_dashboards,
       })
    )

def worksheets_open(request):
    base_url = get_settings('dashboards', 'base_url', None, '')
    project_name = request.GET['project_name']
    project_owner = request.GET['project_owner']
    username = request.user.username
    to_worksheet = base_url+"/dashboards/%s/%s/%s"%(username,project_owner,project_name)
    print(to_worksheet)
    return HttpResponseRedirect(to_worksheet)

urlpatterns = [
    url(r'^$', worksheets, name='worksheets'),
    url(r'^/open$', worksheets_open, name='worksheet-open'),
]