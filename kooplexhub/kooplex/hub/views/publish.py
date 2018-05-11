import logging
import os
import time

from django.conf.urls import url, include
from django.shortcuts import render, redirect
from django.contrib import messages

from kooplex.hub.models import Project, HtmlReport, DashboardReport, ScopeType, ReportDoesNotExist, get_report
from kooplex.lib import authorize, get_settings
from kooplex.lib.filesystem import list_notebooks, list_files, copy_reportfiles_in_place, translate, cleanup_reportfiles
from kooplex.logic.impersonator import publish_htmlreport

logger = logging.getLogger(__name__)

def publishForm(request, project_id):
    """Handles the publication."""
    if not authorize(request):
        return redirect('login')
    if request.method == 'GET':
        project = Project.objects.get(id = project_id)
        scopes = ScopeType.objects.all()
        notebooks = list(list_notebooks(request.user, project))
        files = list(list_files(request.user, project))
        logger.debug('render publish form for project %s' % project)
        return render(
            request,
            'publish/publishform.html',
            context = 
                {
                    'base_url': get_settings('hub', 'base_url'),
                    'project': project,
                    'notebooks': notebooks,
                    'files': files,
                    'scopes': scopes,
                }
        )
    elif request.method == 'POST':
        if 'cancel' in request.POST.keys():
            return redirect('projects')
        project = Project.objects.get(id = project_id)
        name = request.POST['report_name'].strip()
        description = request.POST['report_description'].strip()
        t = translate(request.POST['ipynb_file'])
        if len(name) == 0:
            name, _ = os.path.splitext(os.path.basename(t.path))
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
            notebook_dirname = t.dirname,
            notebook_filename = t.path, 
            scope = scope,
            password = password
        )
        report.notebookfile = t
        report.save()    #FIXME: menteni kell, hogy legyen id a base-hez
        # conversion and deployment
        if isinstance(report, HtmlReport):
            logger.debug('publish new HtmlReport %s' % report)
            publish_htmlreport(report)
        elif isinstance(report, DashboardReport):
            logger.debug('publish new DashboardReport %s' % report)
        files = [ translate(f) for f in request.POST.getlist('other_files') ]
        copy_reportfiles_in_place(report, files)
        report.save()
        logger.info('new report %s published' % report)
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
                messages.error(request, 'Somethng went wrong while deleting report %s [%s]. Ask the administrator to look after the case.' % (report, e))
    if removed == 1:
        messages.info(request, 'A former report instance of project %s has been deleted.' % (project))
    elif removed > 1:
        messages.info(request, '%d former report instances of project %s have been deleted.' % (removed, project))
    return redirect('projects')

urlpatterns = [
    url(r'^/(?P<project_id>\d+)/$', publishForm, name = 'notebook-publishform'), 
]
