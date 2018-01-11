import codecs
import os
from django.conf.urls import url
from django.shortcuts import render, redirect
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.template import RequestContext

from kooplex.hub.models.report import Report
from kooplex.hub.models.user import User
from kooplex.hub.models.scope import ScopeType
from kooplex.hub.models.project import Project, UserProjectBinding
from kooplex.lib.spawner import ReportSpawner
from kooplex.lib.libbase import get_settings


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
    INTERNAL = ScopeType.objects.get(name = 'internal')
    PUBLIC = ScopeType.objects.get(name = 'public')
    if request.user.is_anonymous():
        myreports = []
        internal_good_ = []
        me = None
    else:
        me = request.user
        my_gitlab_id = str( me.gitlab_id )
#FIXME: naming should follow like in the projects: E.g. reports_mine
        myreports = Report.objects.filter(creator = me)
        myprojectbindings = UserProjectBinding.objects.filter(user = me)
        internalreports = Report.objects.filter(scope = INTERNAL)
        projectset = set([ pb.project for pb in myprojectbindings ]).intersection([ r.project for r in internalreports ])
        internalreports_good = filter(lambda r: r.project in projectset, internalreports) 
    publicreports = list( Report.objects.filter(scope = PUBLIC) )
    publicreports.extend(internalreports_good)
    return render(
        request,
        'report/reports.html',
        context_instance = RequestContext(request,
        {
            'user': me,
            'myreports': group_by_project( myreports ),
            'publicreports': group_by_project( publicreports ),
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
        elif report.scope == 'internal' and me in [ r.hub_user for r in report.project.members_]:
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
    filename = request.GET['filename']
    checker = { 'dashboard': filename, 'html': filename.replace('.ipynb', '.html') }
    try:
        project = Project.objects.get(id = project_id)
        reports = list(Report.objects.filter(project = project, scope = 'public'))
        reports.sort()
        found = False
        while len(reports):
            report = reports.pop(0)
            if report.file_name == checker[report.type]:
                found = True
                break
        if not found:
            raise Report.DoesNotExist()
    except Report.DoesNotExist:
        return HttpResponseRedirect(reverse('reports'))
    return HttpResponseRedirect(reverse('report-open') + '?report_id=%d' % report.id)

def container_report_start(request):
    assert isinstance(request, HttpRequest)
    #CHECK how many report servers are running and shutdown the oldest one
    notebooks = Notebook.objects.filter(type="report")
    max_number_of_report_servers =  get_settings('report_server', 'max_number', None, 5)
    if len(notebooks) > max_number_of_report_servers:
        notebook=sorted(notebooks)[0]
        project = Project.objects.get(id=notebook.project_id)
        spawner = ReportSpawner(project=project, image="none", report=None)
        spawner.delete_notebook(notebook)

    report_id = request.GET['report_id']
    report = Report.objects.get(id=report_id)
    if report.image=="":
        report.image = report.project.image

    spawner = ReportSpawner( project=report.project, image=report.image, report=report)
    notebook = spawner.make_notebook()
    notebook = spawner.start_notebook(notebook)

    session = spawner.start_session(notebook, report.target_, 'python3', notebook.name)
    session.report_id = report.id
    session.save()
    return HttpResponseRedirect(notebook.external_url)

def container_report_stop(request):
    assert isinstance(request, HttpRequest)
    report_id = request.GET['report_id']
    report = Report.objects.get(id=report_id)
    notebook = Notebook.objects.filter(username="none",id=report_id)[0]

    spawner = ReportSpawner(project=report.project, image=report.image, report=report)
    spawner.delete_notebook(notebook)
    # Change/Save project status
    # project.session = None
    # project.save()

    return HttpResponseRedirect(HUB_NOTEBOOKS_URL)
    report_id = request.GET['report_id']
    report = Report.objects.get(id=report_id)
    #spawner = ReportSpawner(report, image=report.image)
    spawner = ReportSpawner( project=report.project, image=report.image, report=report)
    notebook = spawner.ensure_notebook_running()

    session = spawner.start_session(report.target_, 'python3', notebook.name, notebook.name)
    session.report_id = report.id
    session.save()
    print_debug("Opening session, Finished")
    return HttpResponseRedirect(reverse('reports'))

def container_report_all_stop(request):
    assert isinstance(request, HttpRequest)
    notebooks = Notebook.objects.filter(type="report")
    for notebook in  notebooks:
        project = Project.objects.get(id=notebook.project_id)
        spawner = ReportSpawner(project=project, image="none", report=None)
        spawner.delete_notebook(notebook)

    return HttpResponseRedirect(reverse('reports'))

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
    url(r'^rstart$', container_report_start, name='report-start'),
    url(r'^reports-stop$', container_report_all_stop, name='report-all-stop'),
    url(r'^openlatest$', openreport_latest, name='report-openlatest'),
    url(r'^settings$', setreport, name='report-settings'),
]

