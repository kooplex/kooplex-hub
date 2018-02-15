import logging
import os
import time

from django.conf.urls import patterns, url, include
from django.shortcuts import render, redirect
from django.template import RequestContext

from kooplex.hub.models import Project, HtmlReport, DashboardReport, ScopeType
from kooplex.lib import authorize, get_settings
from kooplex.lib.filesystem import list_notebooks, list_files, copy_dashboardreport_in_place, translate
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
        elif isinstance(report, DashboardReport):
            files = request.POST.getlist('other_files')
            copy_dashboardreport_in_place(report, files)
        report.save()
        logger.info('new report %s' % report)
    return redirect('projects')

urlpatterns = [
    url(r'^/?$', publishForm, name = 'notebook-publishform'), 
]
