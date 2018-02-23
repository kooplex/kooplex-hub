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
from kooplex.hub.models import ReportDoesNotExist, HtmlReport, DashboardReport, ScopeType, DashboardContainer
from kooplex.hub.models import Project, LimitReached
from kooplex.logic.spawner import spawn_dashboard_container, remove_container

logger = logging.getLogger(__name__)

def reports(request):
    user = request.user
    if authorize(request):
        reports_mine = list_user_reports(user)
        reports_internal = list_internal_reports(user)
        reports_public = list_public_reports(authorized = True)
    else:
        reports_mine = []
        reports_internal = []
        reports_public = list_public_reports(authorized = False)
    context_dict = {
        'user': user,
        'reports_mine': reports_mine,
        'reports_internal': reports_internal,
        'reports_public': reports_public,
    }
    if hasattr(request, 'ask_for_password'):
        logger.debug("Rendering reports.html and ask for password: report id %s" % request.ask_for_password)
        context_dict['ask_for_password'] = int(request.ask_for_password)
    else:
        logger.debug('Rendering reports.html')
    return render(
        request,
        'report/reports.html',
        context_instance = RequestContext(request, context_dict)
    )

def _do_report_open(report):
    if isinstance(report, HtmlReport):
        with codecs.open(report.filename_report_html, 'r', 'utf-8') as f:
            content = f.read()
        logger.debug("Dumping reportfile %s" % report.filename_report_html)
        return HttpResponse(content)
    elif isinstance(report, DashboardReport):
        logger.debug("Starting Dashboard server for %s" % report)
        return redirect(spawn_dashboard_container(report)) #FIXME: launch is not authorized

def _checkpass(report, report_pass):
    if isinstance(report, HtmlReport):
        if len(report.password) == 0:
            logger.debug("Report %s is not password protected" % report)
            return True
        if report.password == report_pass:
            logger.debug("Report password for %s is matching" % report)
            return True
        else:
            logger.debug("Report password for %s is not matching" % report)
            return False
    elif isinstance(report, DashboardReport):
        logger.debug("Report password for %s is not checked, jupyter will take care for it" % report)
        return True

def openreport(request):
    assert isinstance(request, HttpRequest)
    if request.method == 'GET':
        report_id = request.GET['report_id']
        report_pass = None
    elif request.method == 'POST':
        report_id = request.POST['report_id']
        report_pass = request.POST.get('report_pass', '')
    else:
        return redirect('reports')
    try:
        user = request.user
        report = get_report(id = report_id)
        if report.is_user_allowed(user):
            logger.debug('authenticated user %s opens report %s' % (user, report))
            return _do_report_open(report)
        if report.is_public:
            if report_pass is None and request.method == 'GET':
                request.ask_for_password = report_id
                return reports(request)
            elif _checkpass(report, report_pass):
                logger.debug('open public report %s' % (report))
                return _do_report_open(report)
            else:
                messages.error(request, 'You may have mistyped the password')
        else:
            messages.error(request, 'You are not allowed to open this report')
    except ReportDoesNotExist:
        messages.error(request, 'Report does not exist')
    except LimitReached as msg:
        logger.warning(msg)
        messages.error(request, msg)
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
#FIXME: password check redirection
        messages.error(request, 'You are not allowed to open this report.')
    except ReportDoesNotExist:
        messages.error(request, 'Report does not exist')
    return redirect('reports')


def stop_reportcontainer(request):
    assert isinstance(request, HttpRequest)
    containername = request.GET['containername']
    try:
        container = DashboardContainer.objects.get(name = containername) #FIXME: we should authorize by browser id
        remove_container(container)
        logger.info('report container %s is removed' % container)
    except DashboardContainer.DoesNotExist:
        messages.error(request, 'Reportserver container is not found.')
    return redirect('reports')


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
    url(r'^/stop$', stop_reportcontainer, name='report-all-stop'),
    url(r'^/settings$', setreport, name='report-settings'),
]

