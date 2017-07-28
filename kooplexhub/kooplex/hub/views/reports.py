import codecs

from django.conf.urls import url
from django.shortcuts import render, redirect
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.template import RequestContext

from kooplex.hub.models.report import Report
from kooplex.hub.models.user import HubUser
from kooplex.hub.models.project import Project

#from kooplex.lib.libbase import get_settings #TODO: get server prefix

def group_by_project(reports):
    reports_grouped = {}
    for r in reports:
        k = r.project, r.name
        if not k in reports_grouped:
            reports_grouped[k] = []
        reports_grouped[k].append(r)
    for rl in reports_grouped.values():
        rl.sort()
    return reports_grouped

def reports(request):
    assert isinstance(request, HttpRequest)
    if request.user.is_anonymous():
        myreports = []
        internal_good_ = []
        username = None
    else:
        username = request.user.username
        me = HubUser.objects.get(username = username)
        my_gitlab_id = str( HubUser.objects.get(username = username).gitlab_id )
        myreports = Report.objects.filter(creator = me)
        internal_ = Report.objects.filter(scope = 'internal')
        internal_good_ = filter(lambda x: my_gitlab_id in x.project.gids.split(','), internal_)
    publicreports = list( Report.objects.filter(scope = 'public') )
    publicreports.extend(internal_good_)
    return render(
        request,
        'report/reports.html',
        context_instance = RequestContext(request,
        {
            'myreports': group_by_project( myreports ),
            'publicreports': group_by_project( publicreports ),
            'username': username,
       })
    )

def openreport(request):
    assert isinstance(request, HttpRequest)
    report_id = request.GET['report_id']  if request.method == 'GET' else request.POST['report_id']
    try:
        report = Report.objects.get(id = report_id)
    except Report.DoesNotExist:
        return HttpResponseRedirect(reverse('reports'))
    if request.user.is_anonymous():
        if report.scope == 'public':
            pass
        else:
            return HttpResponseRedirect(reverse('reports'))
    else:
        me = HubUser.objects.get(username = request.user.username)
        if report.scope == 'public':
            pass
        elif report.scope == 'internal' and me in report.project.members_:
            pass
        elif report.creator == me:
            pass
        else:
            return HttpResponseRedirect(reverse('reports'))
    if report.type == 'html':
        with codecs.open(report.entry_, 'r', 'utf-8') as f:
            content = f.read()
        return HttpResponse(content)
    elif report.type == 'dashboard':
        return HttpResponseRedirect(report.url_)

def openreport_latest(request):
    assert isinstance(request, HttpRequest)
    project_id = request.GET['project_id']
    try:
        project = Project.objects.get(id = project_id)
        reports = list(Report.objects.filter(project = project, scope = 'public'))
        report = reports.pop()
        while len(reports):
            r = reports.pop()
            if r.ts_created > report.ts_created:
                report = r
    except Report.DoesNotExist:
        return HttpResponseRedirect(reverse('reports'))
    return HttpResponseRedirect(reverse('report-open') + '?report_id=%d' % report.id)

def setreport(request):
    assert isinstance(request, HttpRequest)
    if request.user.is_anonymous():
        return HttpResponseRedirect(reverse('reports'))
    button = request.POST['button']
    try:
        me = HubUser.objects.get(username = request.user.username)
        report_id = request.POST['report_id']
        r = Report.objects.get(id = report_id, creator = me)
        if button == 'apply':
            r.scope = request.POST['scope']
            r.description = request.POST['report_description']
            r.save()
        elif button == 'delete':
            r.remove()
    except Report.DoesNotExist:
        # only the creator is allowed to change the scope of the report
        pass
    return HttpResponseRedirect(reverse('reports'))

urlpatterns = [
    url(r'^$', reports, name = 'reports'),
    url(r'^open$', openreport, name='report-open'),
    url(r'^openlatest$', openreport_latest, name='report-openlatest'),
    url(r'^settings$', setreport, name='report-settings'),
]

