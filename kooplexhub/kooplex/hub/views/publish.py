import time

from django.conf.urls import patterns, url, include
from django.shortcuts import render, redirect
from django.http import HttpRequest
from django.template import RequestContext

from kooplex.hub.models import Project, HtmlReport, DashboardReport, ScopeType
from kooplex.lib import get_settings, list_notebooks, list_files, publish_htmlreport, copy_dashboardreport_in_place

def publishForm(request):
    """Handles the publication."""
    assert isinstance(request, HttpRequest)
    if request.user.is_anonymous():
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
        ipynb_file = request.POST['ipynb_file']
        if len(name) == 0:
            name = ipynb_file.split('/')[-1][:-6]
        password = request.POST['password']
        scope = ScopeType.objects.get(name = request.POST['scope'])
##    #other_files = request.POST.getlist('other_files')
##    #request.POST['reports2remove'] 
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
            notebook_filename = ipynb_file,
            scope = scope,
            password = password
        )
        # conversion and deployment
        if isinstance(report, HtmlReport):
            publish_htmlreport(report)
        elif isinstance(report, DashboardReport):
            files = request.POST.getlist('other_files')
            copy_dashboardreport_in_place(report, files)
        report.save()
    return redirect('projects')

urlpatterns = [
    url(r'^/?$', publishForm, name = 'notebook-publishform'), 
]
