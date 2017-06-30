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

#TODO: rename worksheet -> report

HUB_REPORTS_URL = '/hub/worksheets'

def worksheets(request):
    """Renders the worksheets page"""
    assert isinstance(request, HttpRequest)

    username = request.user.username
    myreports = Report.objects.filter(creator_name = username)
    publicreports = Report.objects.filter(scope = 'public') #TODO: MISSING the list of internal reports (not so trivial filter)

    return render(
        request,
        'app/worksheets.html',
        context_instance = RequestContext(request,
        {
            'title':'Browse worksheets',
            'message':'',
            'myreports': myreports,
            'publicreports': publicreports,
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
    report_id = request.GET['report_id']
    report = Report.objects.get(id = report_id)
    content = open(report.entry_).read()
    return HttpResponse(content)

def reports_unpublish(request):
    report_id = int(request.GET['report_id'])
    r = Report.objects.get(id = report_id)
    r.remove()
    return HttpResponseRedirect(HUB_REPORTS_URL)

def report_changescope(request):
    report_id = int(request.POST['report_id'])
    r = Report.objects.get(id = report_id)
    r.scope = request.POST['scope']
    r.save()
    return HttpResponseRedirect(HUB_REPORTS_URL)

urlpatterns = [
    url(r'^$', worksheets, name='worksheets'),
    url(r'^open$', worksheets_open_html, name='worksheet-open'),
    url(r'^opendashboard$', worksheets_open_as_dashboard, name='worksheet-open-as-dashboard'),
    url(r'^unpublish$', reports_unpublish, name='worksheet-unpublish'),
    url(r'^changescope$', report_changescope, name='reportschangescope'),
]

