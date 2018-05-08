import logging
import codecs
import os

from django.contrib import messages
from django.conf.urls import url
from django.shortcuts import render, redirect
from django.http import HttpRequest, HttpResponse
from django.core.urlresolvers import reverse

from kooplex.lib import authorize, get_settings
from kooplex.lib.filesystem import cleanup_reportfiles
from kooplex.hub.models import list_user_reports, list_internal_reports, list_public_reports, get_report, filter_report, get_project
from kooplex.hub.models import ReportDoesNotExist, HtmlReport, DashboardReport, ScopeType, DashboardContainer
from kooplex.hub.models import Project, LimitReached
from kooplex.hub.models import User
from kooplex.logic.spawner import spawn_dashboard_container, remove_container
from kooplex.hub.views.extra_context import get_pane

logger = logging.getLogger(__name__)

def reports(request):
    ask_pass = request.session.get('ask_for_password', -1)
    logger.debug('method %s, ask_pass %s' % (request.method, ask_pass))
    if request.method == 'POST' and ask_pass == -1:
        report_id = request.POST.get('report_id', None)
        if report_id:
            request.session['report_lastpassword'] = request.POST.get('report_pass', None)
            return redirect(reverse('report-open', kwargs = {'report_id': report_id}))
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
    if ask_pass != -1:
        logger.debug("Rendering reports.html and ask for password: report id %s" % ask_pass)
        context_dict['ask_for_password'] = ask_pass
    if hasattr(request, 'pane'):
        context_dict['pane'] = request.pane
    logger.debug('Rendering reports.html')
    return render(
        request,
        'report/reports.html',
        context = context_dict
    )

def authorized(report, user, report_pass):
    logger.debug("report %s scope %s" % (report, report.scope))
    if report.is_public:
        logger.debug('report %s is public' % report)
        if len(report.password) == 0:
            logger.debug("report %s is not password protected" % report)
            return True
        if report.password == report_pass:
            logger.debug("password for report %s is matching" % report)
            return True
    else:
        logger.debug('report %s is not public' % report)
    allowed = report.is_user_allowed(user)
    logger.debug('can user %s open report %s -> %s' % (user, report, allowed))
    return allowed

def dump_file(filename):
    _, ext = os.path.splitext(filename)
    ext = ext[1:].lower()  # split off the period
    logger.debug('filename %s -> extension: %s' % (filename, ext))
    mime = {
        'html': 'text/html',
        'png': 'image/png',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'pdf': 'application/pdf',
    }
    if ext in mime:
        ct = mime[ext]
        try:
            with open(filename, 'rb') as f:
                logger.debug('dumping %s file %s' % (mime[ext], filename))
                return HttpResponse(f.read(), content_type = ct)
        except Exception as e:
            logger.error('error serving file %s -- %s' % (filename, e))
    else:
        logger.error('error serving file %s -- extension%s  not handled' % (filename, ext))
    return HttpResponse('')

def _allow(request, report):
    logger.debug('access granted to open report %s and its attachments' % report)
    request.session['allowed-%s' % report.id] = True
    if 'ask_for_password' in request.session:
        request.session.pop('ask_for_password')

def openreport(request, report_id):
    assert isinstance(request, HttpRequest)
    last_pass = request.session.get('report_lastpassword', None)
    report_pass = request.POST.get('report_pass', last_pass)
    request.pane = get_pane(request)
    try:
        report = get_report(id = report_id)
        if isinstance(report, DashboardReport):
            logger.debug("Starting Dashboard server for %s" % report)
            return redirect(spawn_dashboard_container(report))
        if authorized(report, request.user, report_pass):
            _allow(request, report)
            return dump_file(report.filename_report_html)
        elif report.is_public:
            logger.debug('asking password for report %s' % report)
            request.session['ask_for_password'] = report.id
            return reports(request)
        else:
            messages.error(request, 'Report does not exist or it is not public.')
            return redirect('reports')
    except ReportDoesNotExist:
        messages.error(request, 'Report does not exist')
    except LimitReached as msg:
        logger.warning(msg)
        messages.error(request, msg)
    return reports(request)

def servefile(request, report_id, path):
    assert isinstance(request, HttpRequest)
    last_pass = request.session.get('report_lastpassword', '')
    report_pass = request.POST.get('report_pass', last_pass)
    request.pane = get_pane(request)
    try:
        report = get_report(id = report_id)
        if isinstance(report, DashboardReport):
            logger.error("Dashboard report %s don't serve file" % report)
            messages.error(request, 'Dashboard report attachments are not accessible directly')
            return reports(request)
        allowed = request.session.get('allowed-%s' % report_id, False)
        if allowed:
            logger.debug('attachment %s of report %s can be opened, based on the session' % (path, report))
            return dump_file(os.path.join(report.report_root, path))
        if authorized(report, request.user, report_pass):
            _allow(request, report)
            return dump_file(os.path.join(report.report_root, path))
        logger.debug('asking password for report %s (%s wants to retrieve component %s)' % (report, request.user, path))
        request.session['ask_for_password'] = report.id
        return reports(request)
    except ReportDoesNotExist:
        messages.error(request, 'Report does not exist')
    return reports(request)


def openreport_latest(request, project_owner, project_name, report_name):
    assert isinstance(request, HttpRequest)
    request.pane = get_pane(request)
    user = request.user
    logger.debug('%s opens report %s from project %s-%s' % (user, report_name, project_owner, project_name))
    try:
        logger.debug('found')
        project_owner_instance = User.objects.get(username = project_owner)
        project = get_project(name = project_name, owner = project_owner_instance)
        logger.debug('found project %s' % (project))
        reports = list(filter_report(project = project, name = report_name))
        reports.sort()
        reports.reverse()
        for report in reports:
            if report.is_user_allowed(user) or report.is_public:
                return redirect(reverse('report-open', kwargs = {'report_id': report.id}))
        messages.error(request, 'You are not allowed to open this report.')
    except User.DoesNotExist:
        logger.warning('Project owner %s does not exist' % (project_owner))
        messages.error(request, 'Report does not exist')
    except Project.DoesNotExist:
        logger.warning('Project %s-%s does not exist' % (project_name, project_owner))
        messages.error(request, 'Report does not exist')
    except ReportDoesNotExist:
        logger.warning('Report %s of project %s-%s does not exist' % (report_name, project_name, project_owner))
        messages.error(request, 'Report does not exist')
    return redirect('reports')


#TODO: update url regexp resolver
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

#TODO: update url regexp resolver
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
            report.password = request.POST['password'].strip()
            report.save()
        elif button == 'delete':
            cleanup_reportfiles(report)
            report.delete()
    except ReportDoesNotExist:
        messages.error(request, 'You are not allowed to configure this report')
    return redirect('reports')

urlpatterns = [
    url(r'^/?$', reports, name = 'reports'),
    url(r'^/open/(?P<report_id>\d+)/$', openreport, name = 'report-open'),
    url(r'^/open/(?P<report_id>\d+)/(?P<path>[\./\w]+)$', servefile, name = 'report-dumpcomponent'),
    url(r'^/openlatest/(?P<project_owner>\w+)-(?P<project_name>\w+)/(?P<report_name>\w+)$', openreport_latest, name = 'report-openlatest'),
    url(r'^/stop$', stop_reportcontainer, name = 'reportcontainer-stop'),
    url(r'^/settings$', setreport, name = 'report-settings'),
]

