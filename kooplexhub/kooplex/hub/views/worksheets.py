import base64

from django.conf.urls import patterns, url, include
from django.shortcuts import render
from django.http import HttpRequest,HttpResponse
from django.template import RequestContext
from datetime import datetime
from django.http import HttpRequest, HttpResponseRedirect

from kooplex.hub.models.report import Report
from kooplex.hub.models.dashboard_server import Dashboard_server
from kooplex.lib.libbase import get_settings
from kooplex.lib.gitlab import Gitlab
from kooplex.lib.spawner import Spawner
from kooplex.lib.debug import *
from kooplex.hub.models.project import Project

import os

HUB_REPORTS_URL = '/hub/worksheets'

def worksheets(request):
    """Renders the worksheets page"""
    assert isinstance(request, HttpRequest)

    username = request.user.username
    list_of_html_reports = Report.objects.filter(type='html')
    list_of_dashboards = Report.objects.filter(type='dashboard')
    for dashboard in list_of_dashboards:
        #if type(dashboard.dashboard_server) == type(Dashboard_server):
            dashboard.url = dashboard.get_url()
            dashboard.cache_url = dashboard.get_cache_url()

    return render(
        request,
        'app/worksheets.html',
        context_instance = RequestContext(request,
        {
            'title':'Browse worksheets',
            'message':'',
            'reports': list_of_html_reports,
            'dashboards': list_of_dashboards,
            'username' : username,
       })
    )

def worksheets_open_as_dashboard(request):
    url = request.GET['url']
    cache_url = request.GET['cache_url']
    D = Dashboards()
    D.clear_cache_temp(cache_url)
    return HttpResponseRedirect(url)

def worksheets_open_html(request):
    #OBSOLETE
    #project_id = request.GET['project_id']
    #file = request.GET['file']
    #g = Gitlab()
    #file_vmi = g.get_file(project_id,file)
    #content=base64.b64decode(file_vmi['content'])
    project_id = request.GET['project_id']
    file = request.GET['file']
#FIXME: path tokens hard coded
    project = Project.objects.get(id=project_id)
    filename = os.path.join(get_settings('users', 'srv_dir', None, ''), 'dashboards', project.image.split('-')[-1], project.home, file)
    content = open(filename).read()
    return HttpResponse(content)

def reports_unpublish(request):
    report_id = int(request.GET['report_id'])
    r = Report.objects.get(id=report_id)
    r.delete()
    return HttpResponseRedirect(HUB_REPORTS_URL)

urlpatterns = [
    url(r'^$', worksheets, name='worksheets'),
    url(r'^open$', worksheets_open_html, name='worksheet-open'),
    url(r'^opendashboard$', worksheets_open_as_dashboard, name='worksheet-open-as-dashboard'),
    url(r'^unpublish$', reports_unpublish, name='worksheet-unpublish'),

]
