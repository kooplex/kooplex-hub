import logging
import json
import time
import os

from django.conf.urls import url
from django.http import HttpRequest, HttpResponse
from django.contrib.auth import authenticate, login, logout

from kooplex.hub.models import User, ScopeType, Project, DashboardReport, HtmlReport, filter_report, get_project
from kooplex.logic.impersonator import publish_htmlreport
from kooplex.lib.filesystem import copy_reportfiles_in_place, cleanup_reportfiles


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


def _translate(whoami, project, filename):
    if filename.startswith('git/'):
        return { 'volname': 'git', 'filename': filename[4:], 'filename_in_hub': '/mnt/volumes/git/%s/%s/%s' % (whoami.username, project.name_with_owner, filename[4:]) }
    elif filename.startswith('share/'):
        return { 'volname': 'share', 'filename': filename[6:], 'filename_in_hub': '/mnt/volumes/share/%s/%s' % (project.name_with_owner, filename[6:]) }
    else:
        return { 'volname': 'home', 'filename': filename, 'filename_in_hub': '/mnt/volumes/home/%s/%s' % (whoami.username, filename) }

def publish(request):
#FIXME: filesystem stuff here!!!
    from distutils import dir_util
    from distutils import file_util

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
        #attach_files = request.POST.getlist('other_files')
        attach_files = request.POST.get('other_files', '').split(',') # FIXME
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
        if deleteformerreports:
            logger.debug('asked to delete former reports')
            for r in filter_report(name = reportname, project = project, creator = request.user):
                cleanup_reportfiles(r)
                r.delete()
                logger.info('ws deleted report: %s' % r)
        else:
            logger.debug('asked to keep former reports')
        t = _translate(whoami, project, notebook_filename)
        filename_in_container = '/home/%s/%s' % (whoami.username, notebook_filename),
        report = reportclass(
            creator = request.user,
            name = reportname,
            description = description,
            ts_created = int(time.time()),
            project = project,
            notebook_dirname = t['volname'],
            notebook_filename = t['filename'],
            scope = scope,
            password = reportpassword
        )
        report.filename_in_hub = t['filename_in_hub']
        report.filename_in_container = filename_in_container
        report.volname = t['volname']
        report.save()    #FIXME: menteni kell, hogy legyen id a base-hez view/publish.py
        # conversion and deployment
        if isinstance(report, HtmlReport):
            publish_htmlreport(report)
        elif isinstance(report, DashboardReport):
            attach_files = [] #FIXME: file attachments are not handled yet
        logger.debug('copy report files %s to report %s' % (attach_files, report))
#FIXME: HACK
        #copy_reportfiles_in_place(report, attach_files)
        for fn in attach_files:
            if len(fn) == 0:
                continue
            t = _translate(whoami, project, fn)
            dest = os.path.join(report.report_root, fn)
            src = t['filename_in_hub']
            logger.debug('copy attachment report %s [req %s] %s -> %s' % (report, fn, src, dest))
            if os.path.isdir(src):
                logger.debug("%s is a folder FIXME" % src)
                pass
            else:
                logger.debug("%s is a file" % src)
                dir_target = os.path.dirname(dest)
                logger.debug("dir_target %s" % dir_target)
                dir_util.mkpath(dir_target)
                logger.debug("mkdired")
                file_util.copy_file(src, dir_target)
                logger.debug("copied")
        report.save()
        logger.info('new report %s' % report)
    except Exception as e:
        logger.error('Exception while publish -- %s' % e)
        return HttpResponse(json.dumps({ 'Error': str(e) }))
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
