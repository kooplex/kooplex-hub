import logging

from django.db import transaction
from django.db import models
from django.conf.urls import url
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import redirect, render
from django_tables2 import RequestConfig
from django.views.generic import ListView, CreateView, UpdateView
from django.urls import reverse_lazy

from hub.models import Image
from hub.models import Report, Container
from hub.forms import FormReport

from kooplex.lib import now, translate_date
from kooplex.settings import KOOPLEX
from kooplex.lib.filesystem import prepare_dashboardreport_withinitcell

logger = logging.getLogger(__name__)



@login_required
def newreport(request):#, next_page):
    """Renders new report form."""
    user = request.user
    logger.debug("user %s, method: %s" % (user, request.method))
    if request.method == 'GET':
        context_dict = {
            'f_report': FormReport(user = user),
            'menu_report': 'active',
            'next_page': 'indexpage', #next_page,
        }
        return render(request, 'report/newreport.html', context = context_dict)
    elif request.method == 'POST' and request.POST['button'] == 'apply':
        try:
            reporttype = request.POST['reporttype']
            index = request.POST['index'] #if reporttype != Report.TP_BOKEH else ''
            image_id = request.POST['image']
            image = Image.objects.get(id = image_id) if image_id != 'None' else 1
            name = request.POST['name']
            tag_name = request.POST['tag_name'] if request.POST['tag_name'] else '--'
            folder = request.POST['folder']
            try:
                prev_report = Report.objects.get(tag_name = tag_name, name = name, creator = user)
                prev_report.delete()
                logger.debug("Previous report with the same tag is removed")
            except Exception as e:
                logger.error(e)
                pass

            Report.objects.create(
                name = name,
                creator = user,
                description = request.POST['description'], 
                reporttype = reporttype,
                index = index,
                image = image,
                folder = folder,
                password = request.POST['password'] if 'password' in request.POST else '',
                tag_name = tag_name if tag_name else 'latest',
                subcategory_name = request.POST['subcategory_name'] if 'subcategory_name' in request.POST else 'default',
            )
            messages.info(request, "Report %s is created" % request.POST['name'])
            return redirect('report:list')
        except Exception as e:
            logger.error(e)
            raise
    else:
        return redirect('indexpage')

def load_files(request):
    user = request.user
    folder_name = request.GET.get('folder')
    files = list(user.profile.files_reportprepare(folder_name))
    logger.debug("report file %s" % (files[0]))
    return render(request, 'report/newreport_files_dropdown.html', context = { 'files': files })

#@login_required
def listreport(request, files = []):#, next_page):
    """Renders new report list."""
    user = request.user
    logger.debug("user %s, method: %s" % (user, request.method))
    if (request.method == 'POST' and request.POST.get('button', 'search') == 'search') or request.method == 'GET':
        pattern = request.POST.get('name', '')
        report_cats = filter_reports(user, pattern)
        #table = table_collaboration(project)
        #table_collaborators = table(user.profile.everybodyelse) if pattern == '' else table(user.profile.everybodyelse_like(pattern))
    elif request.method == 'POST' and request.POST.get('button') == 'showall':
        report_cats = filter_reports(user)
    else:
        report_cats = filter_reports(user)

    context_dict = {
        'menu_report': 'active',
        'next_page': 'indexpage', #next_page,
        'report_cats' : report_cats,
        'files' : files,
    }
    return render(request, 'report/list.html', context = context_dict)

#FIXME https://django-taggit.readthedocs.io/en/latest/getting_started.html
def filter_reports(user, pattern = ''):
    from .report import Report
    from hub.forms import T_REPORTS, T_REPORTS_DEL
    
    report_cats = {}
    if pattern:
        query_reports = Report.objects.filter(models.Q(subcategory_name__icontains = pattern) | models.Q(name__icontains = pattern) )
    else:
        query_reports = Report.objects.all()
        
    # The structure is
    # subcategory
    #  - tag_name

    for report in query_reports:

        g = report.groupby()
        T = T_REPORTS_DEL(g) if user == report.creator else T_REPORTS(g)
        logger.debug("RReport: %s ? %s - subcategory: %s, tag: %s" % (report.name, report.creator, report.subcategory_name, report.tag_name))
        if report.subcategory_name in report_cats.keys():
            report_cats[report.subcategory_name].append((report, T))
            for iv,v in enumerate(report_cats[report.subcategory_name]):
                logger.debug("RReport: %s ? %s, %s ? %s - subcategory: %s" % (report.name, v[0].name, report.creator, v[0].creator, report.subcategory_name))
                if report.name == v[0].name and report.creator == v[0].creator and report.tag_name != v[0].tag_name:
                    report_cats[report.subcategory_name].pop(iv)
#                    report_cats[report.subcategory_name].append((report.latest, T))
                    
#                else:
    #                report_cats[report.subcategory_name].append((report.latest, T))
#                    logger.debug("RReport: len %d " %len(report_cats) )
        else:
            report_cats[report.subcategory_name] = []
            report_cats[report.subcategory_name].append((report, T))
    return report_cats

#@login_required
def openreport(request, report_id):
    """Renders new report list."""
    user = request.user
    logger.debug("user %s, method: %s" % (user, request.method))
    try:
        report = Report.objects.get(id = report_id)
    except Exception as e:
        logger.warning('Cannot resolve report id: %s -- %s' % (report_id, e))
        return redirect('indexpage')
    if report.reporttype == report.TP_STATIC: 
        url_external = report.url_external
        logger.debug('redirect: %s' % url_external)
        return redirect(url_external)
    elif report.reporttype == report.TP_DYNAMIC:
        container = Container.get_reportcontainer(report, create = True)
        container.docker_start()
        url_external = "%s/notebook/%s/notebooks/%s?token=%s" % (KOOPLEX.get('base_url', 'localhost'), container.name, report.index, user.profile.token)
        logger.debug('redirect: %s ' % url_external)
        return redirect(url_external)
    elif report.reporttype == report.TP_BOKEH:
        container = Container.get_reportcontainer(report, create = True)
        container.docker_start()
        url_external = "%s/notebook/%s/report" % (KOOPLEX.get('base_url', 'localhost'), container.name)
        logger.debug('redirect: %s' % url_external)
        return redirect(url_external)
    elif report.reporttype == report.TP_SERVICE:
        container = Container.get_reportcontainer(report, create = True)
        container.docker_start()
        url_external = "%s/notebook/%s/report/help" % (KOOPLEX.get('base_url', 'localhost'), container.name)
        msg = "Report %s is started. API is at %s" % (report.name, url_external)
        logger.info(msg)
        messages.info(request, msg)
        return redirect('report:list')
    messages.error(request, "Rendering report type %s is not implemeted yet" % report.reporttype)
    return redirect('report:list')


@login_required
def deletereport(request, report_id):
    user = request.user
    logger.debug("user %s, method: %s" % (user, request.method))
    try:
        report = Report.objects.get(id = report_id, creator = user)
        report.delete()
        messages.info(request, "Deleted your report: %s" % report)
    except Exception as e:
        logger.warning('Cannot remove report id: %s -- %s' % (report_id, e))
        messages.warning(request, "Cannot delete requested report.")
    return redirect('report:list')



urlpatterns = [
    url(r'^newreport/?$', newreport, name = 'new'),
    url(r'^listreport/?$', listreport, name = 'list'),
    url(r'^filter_reports/?$', listreport, name = 'filter_reports'),
    url(r'^openreport/(?P<report_id>\d+)$', openreport, name = 'openreport'),
    url(r'^deletereport/(?P<report_id>\d+)$', deletereport, name = 'deletereport'), 

    url(r'^load_files/?$', load_files, name = 'ajax_load_files'),  

 ]
