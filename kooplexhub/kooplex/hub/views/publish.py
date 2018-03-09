import logging
import os
import time

from django.conf.urls import url, include
from django.shortcuts import render, redirect
from django.template import RequestContext
from django.contrib import messages

from kooplex.hub.models import Project, HtmlReport, DashboardReport, ScopeType, ReportDoesNotExist, get_report
from kooplex.lib import authorize, get_settings
from kooplex.lib.filesystem import list_notebooks, list_files, copy_reportfiles_in_place, translate, cleanup_reportfiles
from kooplex.logic.impersonator import publish_htmlreport

logger = logging.getLogger(__name__)

def publishForm(request):
    """Handles the publication."""
    if not authorize(request):
        return redirect('login')
    if request.method == 'GET':
        try:
            project_id = request.GET['project_id']
        except KeyError:
            return redirect('reports')
        project = Project.objects.get(id = project_id)
        reports = list(project.reports)
        scopes = ScopeType.objects.all()
        notebooks = list(list_notebooks(request.user, project))
        files = list(list_files(request.user, project))
        logger.debug('render publish form for project %s' % project)
        return render(
            request,
            'publish/publishform.html',
            context_instance = RequestContext(request,
                {
                    'base_url': get_settings('hub', 'base_url'),
                    'project_id': project_id,
                    'reports': reports,
                    'notebooks': notebooks,
                    'files': files,
                    'scopes': scopes,
                })
        )
    elif request.method == 'POST':
        if 'cancel' in request.POST.keys():
            return redirect('projects')
        project = Project.objects.get(id = request.POST['project_id'])
        name = request.POST['report_name'].strip()
        description = request.POST['report_description'].strip()
        t = translate(request.POST['ipynb_file'])
        if len(name) == 0:
            name, _ = os.path.splitext(os.path.basename(t['filename_in_container']))
        password = request.POST['password']
        scope = ScopeType.objects.get(name = request.POST['scope'])
        if 'html' in request.POST.keys():
            reportclass = HtmlReport
        elif 'dashboard' in request.POST.keys():
            reportclass = DashboardReport
        else:
            return redirect('projects')
        report = reportclass(
            creator = request.user,
            name = name,
            description = description,
            ts_created = int(time.time()),
            project = project,
            notebook_filename = t['filename_in_mount'], #NOTE: we may need the volume as well!
            scope = scope,
            password = password
        )
        report.filename_in_hub = t['filename_in_hub']
        report.filename_in_container = t['filename_in_container']
        report.volname = t['volname']
        # conversion and deployment
        if isinstance(report, HtmlReport):
            publish_htmlreport(report)
            #files = request.POST.getlist('other_files')
            #copy_reportfiles_in_place(report, files)
        elif isinstance(report, DashboardReport):
            files = request.POST.getlist('other_files')
            copy_reportfiles_in_place(report, files)
        report.save()
        logger.info('new report %s' % report)
        messages.info(request, 'Your new report named %s of project %s is publised.' % (report.name, project))
        removed = 0
        for report_id in request.POST.getlist('report2remove'):
            try:
                report = get_report(id = report_id, creator = request.user)
                cleanup_reportfiles(report)
                report.delete()
                logger.info("deleted report %s" % report)
                removed += 1
            except ReportDoesNotExist:
                logger.warning("not found reportid %d and user %s" % (report_id, request.user))
                messages.warning(request, 'You are not allowed to manipulate report with id %d' % report_id)
            except Exception as e:
                logger.error("cannot delete report %s -- %s" % (report, e))
                messages.error(request, 'Somethng went wrong while deleting report %s [%s]. Ask the administraotr to look after the case.' % (report, e))
    if removed == 1:
        messages.info(request, 'A former report instance of project %s has been deleted.' % (project))
    elif removed > 1:
        messages.info(request, '%d former report instances of project %s have been deleted.' % (project))
    return redirect('projects')

urlpatterns = [
    url(r'^/?$', publishForm, name = 'notebook-publishform'), 
]
