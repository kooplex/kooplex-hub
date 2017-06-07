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
    cache_url = request.GET['cache_url']
    D = Dashboards()
    D.clear_cache_temp(cache_url)
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
    report_type = request.GET['report_type']
    file = request.GET['file']
    d = Dashboards()
    if report_type=="html":
        d.unpublish_html(project_id,file)

    if report_type == "dashboard":
        project_name = request.GET['project_name']
        image_type = request.GET['image_type']
        creator_name = request.GET['creator_name']
        username = request.user.username
        d.unpublish_dashboard(project_id, image_type, username, creator_name, project_name, file)

    return HttpResponseRedirect(HUB_REPORTS_URL)

urlpatterns = [
    url(r'^$', worksheets, name='worksheets'),
    url(r'^open$', worksheets_open_html, name='worksheet-open'),
    url(r'^opendashboard$', worksheets_open_as_dashboard, name='worksheet-open-as-dashboard'),
    url(r'^unpublish$', reports_unpublish, name='worksheet-unpublish'),

]