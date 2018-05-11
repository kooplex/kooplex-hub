import logging
import json
import time
import os

from django.conf.urls import url
from django.http import HttpRequest, HttpResponse
from django.contrib.auth import authenticate, login, logout

from kooplex.hub.models import User, ScopeType, Project, DashboardReport, HtmlReport, filter_report, get_project
from kooplex.logic.impersonator import publish_htmlreport
from kooplex.lib.filesystem import copy_reportfiles_in_place, cleanup_reportfiles, FileOrFolder
from kooplex.lib import get_settings

logger = logging.getLogger(__name__)

def echo(request):
    assert isinstance(request, HttpRequest)
    if request.method == 'GET':
        return HttpResponse(json.dumps({ 'method': request.method, 'GET': request.GET }))
    if request.method == 'POST':
        return HttpResponse(json.dumps({ 'method': request.method, 'POST': request.POST }))

def auth(request):
    assert isinstance(request, HttpRequest) and request.method == 'POST'
    try:
        username = request.POST.get('username', '')
        password = request.POST.get('password', '')
        user = authenticate(username = username, password = password)
        login(request, user)
        logger.info('ws login %s' % (user))
    except Exception as e:
        logger.error('Not authenticated -- %s' % e)
        return HttpResponse(json.dumps({ 'Error': str(e) }))
    return HttpResponse(json.dumps({ 'Status': 200 }))


def _translate(user, project, path):
    if path.startswith('git/'):
        return FileOrFolder(os.path.join(get_settings('volumes', 'git'), user.username, project.name_with_owner, path[4:]))
    elif path.startswith('share/'):
        return FileOrFolder(os.path.join(get_settings('volumes', 'share'), project.name_with_owner, path[6:]))
    else:
        return FileOrFolder(os.path.join(get_settings('volumes', 'home'), user.username, path))

def publish(request):

#NOTE: some part of the code is a duplicate (view/publish.py). May make sense to converge
    assert isinstance(request, HttpRequest) and request.method == 'POST'
    try:
        whoami = request.user
        projectname = request.POST.get('projectname', '')
        projectownerusername = request.POST.get('projectownerusername', '')
        reportname = request.POST.get('reportname', '')
        reporttype = request.POST.get('htmlreport', 'htmlreport')
        reportscope = request.POST.get('scope', 'public')
        reportpassword = request.POST.get('reportpassword', '')
        description = request.POST.get('description', 'An automated report issued by %s' % request.user)
        notebook_filename = request.POST.get('notebook_filename', '')
        attach_files = request.POST.get('other_files', '').split(',') # FIXME: not handled if ',' in filename
        deleteformerreports = bool(request.POST.get('deleteformerreports', 'True'))
        scope = ScopeType.objects.get(name = reportscope)
        projectowner = User.objects.get(username = projectownerusername)
        project = get_project(name = projectname, owner = projectowner)
        if projectowner != request.user and request.user not in project.collaborators:
            logger.error('ws unauthorized to publish: user: %s project: %s (owned by %s)' % (request.user, project, projectowner))
            return HttpResponse(json.dumps({ 'Error': 'You are not authorized to publish that particular report' }))
        if reporttype == 'htmlreport':
            reportclass = HtmlReport
        elif reporttype == 'dashboardreport':
            reportclass = DashboardReport
        else:
            logger.error('ws wrong scope: user: %s scopetype: %s' % (request.user, reporttype))
            return HttpResponse(json.dumps({ 'Error': 'Wrong scopetype: %s (htmlreport|dashboardreport)' % reporttype }))

        logger.info('ws authorized to publish %s: user: %s project: %s (owned by %s)' % (reportname, request.user, project, projectowner))
        del_oops = False
        if deleteformerreports:
            logger.debug('asked to delete former reports')
            for r in filter_report(name = reportname, project = project, creator = request.user):
                try:
                    cleanup_reportfiles(r)
                    r.delete()
                    logger.info('ws deleted report %s' % r)
                except Exception as e:
                    logger.error('ws cannot delete report %s -- %s' % (r, e))
                    del_oops = True
        else:
            logger.debug('asked to keep former reports')
        t = _translate(whoami, project, notebook_filename)
        report = reportclass(
            creator = request.user,
            name = reportname,
            description = description,
            ts_created = int(time.time()),
            project = project,
            notebook_dirname = t.dirname,
            notebook_filename = t.path,
            scope = scope,
            password = reportpassword
        )
        report.notebookfile = t
        report.save()    #FIXME: menteni kell, hogy legyen id a base-hez view/publish.py
        # conversion and deployment
        if isinstance(report, HtmlReport):
            publish_htmlreport(report)
        elif isinstance(report, DashboardReport):
            attach_files = [] #FIXME: file attachments are not handled yet
        logger.debug('copy report files %s to report %s' % (attach_files, report))
        files = [ _translate(whoami, project, f) for f in attach_files ]
        copy_reportfiles_in_place(report, files)
        report.save()
        logger.info('new report %s' % report)
    except Exception as e:
        logger.error('Exception while publish -- %s' % e)
        return HttpResponse(json.dumps({ 'Error': str(e) }))
    if del_oops:
        return HttpResponse(json.dumps({ 'Status': 200, 'Warning': 'Could not properly delete former reports' }))
    return HttpResponse(json.dumps({ 'Status': 200 }))

def closesession(request):
    assert isinstance(request, HttpRequest) and request.method == 'POST'
    try:
        logout(request)
        logger.info('ws logout %s' % (request.user))
    except Exception as e:
        logger.error('Exception while logout -- %s' % e)
        return HttpResponse(json.dumps({ 'Error': str(e) }))
    return HttpResponse(json.dumps({ 'Status': 200 }))

urlpatterns = [
    url(r'^/echo$', echo),
    url(r'^/authenticate$', auth),
    url(r'^/publish$', publish),
    url(r'^/closesession$', closesession),
]
