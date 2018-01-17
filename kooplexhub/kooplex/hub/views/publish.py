import time

from django.conf.urls import patterns, url, include
from django.shortcuts import render, redirect
from django.http import HttpRequest
from django.template import RequestContext

from kooplex.hub.models import Project, HtmlReport, DashboardReport, ScopeType
from kooplex.lib import list_notebooks

class fileinfo:
    def __init__(self, fn, volume, filename):
        self.fullpath = fn
        self.volume = volume
        self.filename = filename

def publishForm(request):
    """Handles the publication."""
    assert isinstance(request, HttpRequest)
    if request.user.is_anonymous():
        return redirect('login')

    if request.method == 'GET':
        project_id = request.GET['project_id']
        project = Project.objects.get(id = project_id)
        reports = list(HtmlReport.objects.filter(project = project))
        reports.extend( list(DashboardReport.objects.filter(project = project)) )
        scopes = ScopeType.objects.all()
        notebooks = [ fileinfo(*x) for x in list_notebooks(request.user, project) ]
        return render(
            request,
            'publish/publishform.html',
            context_instance = RequestContext(request,
                {
                    'notebooks': notebooks,
                    'scopes': scopes,
                    'other_files': [],
                    'project_id': project_id,
                    'reports': reports,
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
            return redirect('project')
        report = reportclass(
            creator = request.user,
            name = name,
            description = description,
            report_type = reporttype,
            ts_created = int(time.time()),
            project = project,
            notebook_filename = ipynb_file,
            scope = scope,
            password = password
        )
        # conversion and deployment
        if isinstance(report, HtmlReport):
            # docker_exec
            raise NotImplementedError
        elif isinstance(report, DashboardReport):
            raise NotImplementedError
        report.save()
    redirect('project')

urlpatterns = [
    url(r'^/?$', publishForm, name = 'notebook-publishform'), 
]
