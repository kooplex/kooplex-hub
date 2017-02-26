import base64

from django.conf.urls import patterns, url, include
from django.shortcuts import render
from django.http import HttpRequest,HttpResponse
from django.template import RequestContext
from datetime import datetime
from django.http import HttpRequest, HttpResponseRedirect


from kooplex.lib.libbase import get_settings
from kooplex.lib.gitlab import Gitlab
from kooplex.lib.spawner import Spawner
from kooplex.lib.dashboards import Dashboards
from kooplex.lib.debug import *

HUB_REPORTS_URL = '/hub/worksheets'

def worksheets(request):
    """Renders the worksheets page"""
    assert isinstance(request, HttpRequest)

    username = request.user.username
    dashboard_url="http://polc.elte.hu:3000"
    D = Dashboards()
    list_of_reports = D.list_reports_html(request)
    list_of_dashboards = D.list_dashboards(request)
    return render(
        request,
        'app/worksheets.html',
        context_instance = RequestContext(request,
        {
            'title':'Browse worksheets',
            'message':'',
            'dashboard_url': dashboard_url,
            'reports': list_of_reports,
            'dashboards': list_of_dashboards,
            'username' : username,
       })
    )

def worksheets_open_as_dashboard(request):
    url = request.GET['url']
    return HttpResponseRedirect(url)

def worksheets_open_html(request):
    project_id = request.GET['project_id']
    file = request.GET['file']
    g = Gitlab()
    file_vmi = g.get_file(project_id,file)
    content=base64.b64decode(file_vmi['content'])
    return HttpResponse(content)

def reports_unpublish(request):
    project_id = request.GET['project_id']
    project_name = request.GET['project_name']
    file = request.GET['file']
    g = Gitlab()
    project = g.get_project_by_name(project_name)[0]
    d = Dashboards()
    d.unpublish(project_id,project,file)

    return HttpResponseRedirect(HUB_REPORTS_URL)

def reports_unpublish_dashboard(request):
    project_id = request.GET['project_id']
    project_name = request.GET['project_name']
    file = request.GET['file']
    d = Dashboards()
    d.unpublish_dashboard(project_id,project_name,file)

    return HttpResponseRedirect(HUB_REPORTS_URL)

urlpatterns = [
    url(r'^$', worksheets, name='worksheets'),
    url(r'^/open$', worksheets_open_html, name='worksheet-open'),
    url(r'^/opendashboard$', worksheets_open_as_dashboard, name='worksheet-open-as-dashboard'),
    url(r'^/unpublish$', reports_unpublish, name='worksheet-unpublish'),

]