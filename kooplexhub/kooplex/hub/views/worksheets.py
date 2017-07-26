import base64
import codecs

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
from kooplex.hub.models.user import HubUser
from kooplex.hub.models.project import Project

import os

#TODO: rename worksheet -> report

HUB_REPORTS_URL = '/hub/worksheets'

def worksheets(request):
    """Renders the worksheets page"""
    assert isinstance(request, HttpRequest)

    username = request.user.username
    try:
        me = HubUser.objects.get(username = username)
        my_gitlab_id = str( HubUser.objects.get(username = username).gitlab_id )
        myreports = Report.objects.filter(creator = me)
    except:
        # unauthenticated
        myreports = []
    publicreports = list( Report.objects.filter(scope = 'public') )
    try:
        internal_ = Report.objects.filter(scope = 'internal')
        internal_good_ = filter(lambda x: my_gitlab_id in x.project.gids.split(','), internal_)
        publicreports.extend(internal_good_)
    except:
        # unauthenticated
        pass

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
#FIXME: check if authorization is enforced by the dashboard
    url = request.GET['url']
    cache_url = request.GET['cache_url']
    D = Dashboards()
    D.clear_cache_temp(cache_url)
    return HttpResponseRedirect(url)

def worksheets_open_html(request):
    report_id = request.GET['report_id']
    try:
        report = Report.objects.get(id = report_id)
    except Report.DoesNotExist:
        return HttpResponseRedirect(HUB_REPORTS_URL)
    if request.user.is_anonymous():
        if report.scope == 'public':
            pass
    else:
        me = HubUser.objects.get(username = request.user.username)
        if report.scope == 'internal' and me in report.project.members_:
            pass
        elif report.scope == 'private' and report.creator == me:
            pass
        else:
            return HttpResponseRedirect(HUB_REPORTS_URL)
    with codecs.open(report.entry_, 'r', 'utf-8') as f:
        content = f.read()
    return HttpResponse(content)

def reports_unpublish(request):
    if request.user.is_anonymous():
        return HttpResponseRedirect(HUB_REPORTS_URL)
    try:
        me = HubUser.objects.get(username = request.user.username)
        report_id = int(request.GET['report_id'])
        r = Report.objects.get(id = report_id, creator = me)
        r.remove()
    except Report.DoesNotExist:
        # only the creator is allowed to remove the report
        pass
    return HttpResponseRedirect(HUB_REPORTS_URL)

def report_changescope(request):
    if request.user.is_anonymous():
        return HttpResponseRedirect(HUB_REPORTS_URL)
    try:
        me = HubUser.objects.get(username = request.user.username)
        report_id = int(request.POST['report_id'])
        r = Report.objects.get(id = report_id)
        r.scope = request.POST['scope']
        r.save()
    except Report.DoesNotExist:
        # only the creator is allowed to change the scope of the report
        pass
    return HttpResponseRedirect(HUB_REPORTS_URL)

urlpatterns = [
    url(r'^$', worksheets, name='worksheets'),
    url(r'^open$', worksheets_open_html, name='worksheet-open'),
    url(r'^opendashboard$', worksheets_open_as_dashboard, name='worksheet-open-as-dashboard'),
    url(r'^unpublish$', reports_unpublish, name='worksheet-unpublish'),
    url(r'^changescope$', report_changescope, name='reportschangescope'),
]

