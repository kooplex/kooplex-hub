import logging
import codecs
import os

from django.contrib import messages
from django.conf.urls import url
from django.shortcuts import render, redirect
from django.http import HttpRequest, HttpResponse
from django.core.urlresolvers import reverse
from django.template import RequestContext

from kooplex.lib import authorize, get_settings
from kooplex.lib.filesystem import cleanup_reportfiles
from kooplex.hub.models import list_user_reports, list_internal_reports, list_public_reports, get_report, filter_report
from kooplex.hub.models import ReportDoesNotExist, HtmlReport, DashboardReport, ScopeType
from kooplex.hub.models import Project
from kooplex.logic.spawner import spawn_dashboard_container

logger = logging.getLogger(__name__)

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
    user = request.user
    if authorize(request):
        reports_mine = list(list_user_reports(user))
        reports_internal = list(list_internal_reports(user))
    else:
        reports_mine = []
        reports_internal = []
    reports_public = list(list_public_reports())
    logger.debug('Rendering reports.html')
    return render(
        request,
        'report/reports.html',
        context_instance = RequestContext(request,
        {
            'user': user,
            'base_url': get_settings('hub', 'base_url'),
            'reports_mine': group_by_project( reports_mine ),
            'reports_internal': group_by_project( reports_internal ),
            'reports_public': group_by_project( reports_public ),
       })
    )

def _do_report_open(report):
    if isinstance(report, HtmlReport):
        with codecs.open(report.filename_report_html, 'r', 'utf-8') as f:
            content = f.read()
        logger.debug("Dumping reportfile %s" % report.filename_report_html)
        return HttpResponse(content)
    elif isinstance(report, DashboardReport):
        logger.debug("Starting Dashboard server for %s" % report)
        return redirect(spawn_dashboard_container(report)) #FIXME: launch is not autgorized

def openreport(request):
    assert isinstance(request, HttpRequest)
    if request.method == 'GET':
        report_id = request.GET['report_id']
    elif request.method == 'POST':
        report_id = request.POST['report_id']
    else:
        return redirect('reports')
    try:
        user = request.user
        report = get_report(id = report_id)
        if report.is_user_allowed(user):
            logger.debug('open report: %s' % report)
            return _do_report_open(report)
        else:
            messages.error(request, 'You are not allowed to open this report')
    except ReportDoesNotExist:
        messages.error(request, 'Report does not exist')
    return redirect('reports')
    

def openreport_latest(request):
    assert isinstance(request, HttpRequest)
    project_id = request.GET['project_id']
    name = request.GET['name']
    try:
        user = request.user
        project = Project.objects.get(id = project_id)
        reports = list(filter_report(project = project, name = name))
        reports.sort()
        reports.reverse()
        for report in reports:
            if report.is_user_allowed(user):
                return _do_report_open(report)
        messages.error(request, 'You are not allowed to open this report')
    except ReportDoesNotExist:
        messages.error(request, 'Report does not exist')
    return redirect('reports')



### ### def container_report_start(request):
### ### #FIXME: needs revision and error handling
### ###     assert isinstance(request, HttpRequest)
### ###     #CHECK how many report servers are running and shutdown the oldest one
### ###     notebooks = Notebook.objects.filter(type="report")
### ###     max_number_of_report_servers =  get_settings('report_server', 'max_number', None, 5)
### ###     if len(notebooks) > max_number_of_report_servers:
### ###         notebook=sorted(notebooks)[0]
### ###         project = Project.objects.get(id=notebook.project_id)
### ###         spawner = ReportSpawner(project=project, image="none", report=None)
### ###         spawner.delete_notebook(notebook)
### ### 
### ###     report_id = request.GET['report_id']
### ###     report = Report.objects.get(id = report_id)
### ###     if report.image == "":
### ###         report.image = report.project.image
### ### 
### ###     spawner = ReportSpawner( project = report.project, image = report.image, report = report)
### ###     notebook = spawner.make_notebook()
### ###     notebook = spawner.start_notebook(notebook)
### ### 
### ###     session = spawner.start_session(notebook, report.target_, 'python3', notebook.name)
### ###     session.report_id = report.id
### ###     session.save()
### ###     return HttpResponseRedirect(notebook.external_url)
### ### 
### ### def container_report_stop(request):
### ### #FIXME: needs revision and error handling
### ###     assert isinstance(request, HttpRequest)
### ###     report_id = request.GET['report_id']
### ###     report = Report.objects.get(id=report_id)
### ###     notebook = Notebook.objects.filter(username="none",id=report_id)[0]
### ### 
### ###     spawner = ReportSpawner(project=report.project, image=report.image, report=report)
### ###     spawner.delete_notebook(notebook)
### ###     # Change/Save project status
### ###     # project.session = None
### ###     # project.save()
### ### 
### ###     return HttpResponseRedirect(HUB_NOTEBOOKS_URL)
### ###     report_id = request.GET['report_id']
### ###     report = Report.objects.get(id=report_id)
### ###     #spawner = ReportSpawner(report, image=report.image)
### ###     spawner = ReportSpawner( project=report.project, image=report.image, report=report)
### ###     notebook = spawner.ensure_notebook_running()
### ### 
### ###     session = spawner.start_session(report.target_, 'python3', notebook.name, notebook.name)
### ###     session.report_id = report.id
### ###     session.save()
### ###     print_debug("Opening session, Finished")
### ###     return HttpResponseRedirect(reverse('reports'))
### ### 
### ### def container_report_all_stop(request):
### ###     assert isinstance(request, HttpRequest)
### ###     notebooks = Notebook.objects.filter(type="report")
### ###     for notebook in  notebooks:
### ###         project = Project.objects.get(id=notebook.project_id)
### ###         spawner = ReportSpawner(project=project, image="none", report=None)
### ###         spawner.delete_notebook(notebook)
### ### 
### ###     return HttpResponseRedirect(reverse('reports'))

def setreport(request):
    if not authorize(request):
        return redirect('reports')
    if request.method != 'POST':
        return redirect('reports')
    button = request.POST['button']
    try:
        user = request.user
        report_id = request.POST['report_id']
        report = get_report(id = report_id, creator = user)
        if button == 'apply':
            report.scope = ScopeType.objects.get(name = request.POST['scope'])
            report.description = request.POST['report_description'].strip()
            report.save()
        elif button == 'delete':
            cleanup_reportfiles(report)
            report.delete()
    except ReportDoesNotExist:
        messages.error(request, 'You are not allowed to configure this report')
    return redirect('reports')


urlpatterns = [
    url(r'^/?$', reports, name = 'reports'),
    url(r'^/open$', openreport, name='report-open'),
    url(r'^/openlatest$', openreport_latest, name='report-openlatest'),
#    url(r'^rstart$', container_report_start, name='report-start'),
#    url(r'^reports-stop$', container_report_all_stop, name='report-all-stop'),
    url(r'^/settings$', setreport, name='report-settings'),
]

