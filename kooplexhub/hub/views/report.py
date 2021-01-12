import logging
import re

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

from hub.models import Image, Project
from hub.models import Report, ReportServiceBinding, Service
from hub.forms import FormReport

from kooplex.lib import now, translate_date, custom_redirect
from kooplex.settings import KOOPLEX
from kooplex.lib.filesystem import prepare_dashboardreport_withinitcell


logger = logging.getLogger(__name__)


@login_required
def newreport(request):#, next_page):
    """Renders new report form."""
    user = request.user
    logger.debug("user %s, method: %s" % (user, request.method))
    if request.method == 'GET':
        fr = FormReport(user = user)
        context_dict = {
            'f_report': fr,
            'menu_report': 'active',
            'next_page': 'indexpage', #next_page,
        }
        return render(request, 'report/newreport.html', context = context_dict)
    elif request.method == 'POST' and request.POST['button'] == 'apply':
        try:
            name = request.POST['name']
            description = request.POST['description']
            image_id = request.POST['image']
            image = Image.objects.get(id = image_id)
            #scope
            #password
            _, project_id, folder, index, _ = re.split(r'^\((\d+),([^,]+),([^,]+)\)$', request.POST['index_selector'])
            #FIXME: nem lehet , a dir/index fájlnevekben
            project = Project.objects.get(id = project_id)
            try:
                prev_report = Report.objects.get(name = name, creator = user, project = project)
                prev_report.delete()
                logger.debug("Previous report with the same tag is removed")
            except Exception as e:
                logger.error(e)
                pass

            Report.objects.create(
                name = name,
                creator = user,
                description = description,
                index = index,
                image = image,
                project = project,
                folder = folder,
                password = request.POST['password'] if 'password' in request.POST else '',
            )
            messages.info(request, "Report %s is created" % request.POST['name'])
            return redirect('report:list')
        except Exception as e:
            logger.error(e)
            raise
    else:
        return redirect('indexpage')


#@login_required
def listreport(request, files = []):#, next_page):
    """Renders new report list."""
    user = request.user
    logger.debug("user %s, method: %s" % (user, request.method))
    if (request.method == 'POST' and request.POST.get('button', 'search') == 'search') or request.method == 'GET':
        pattern = request.POST.get('name', '')
        if pattern:
            reports = Report.objects.filter(name__icontains = pattern)
        else:
            reports = Report.objects.all()
    else:
        raise NotImplementedError("ide hogy kerulsz?")

    context_dict = {
        'menu_report': 'active',
        'next_page': 'indexpage', 
        'reports' : reports,
    }
    return render(request, 'report/list.html', context = context_dict)
#    return render(request, 'report/list_thumbnail.html', context = context_dict)

#@login_required
def openreport(request, report_id):
    """Opens report pod/container."""
    user = request.user
    logger.debug("user %s, method: %s" % (user, request.method))
    try:
        report = Report.objects.get(id = report_id)
        environment = ReportServiceBinding.objects.get(report = report).service
        if environment.state in [ Service.ST_RUNNING, Service.ST_NEED_RESTART ]:
            environment.wait_until_ready()
            if environment.default_proxy.token_as_argument:
                return custom_redirect(environment.url_public, token = environment.user.profile.token)
            else:
                return custom_redirect(environment.url_public)
        else:
            messages.error(request, f'Cannot open {environment.name} of state {environment.state}')
    except ReportServiceBinding.DoesNotExist:
        messages.error(request, 'Environment is missing')
    return redirect('report:list')

@login_required
def deletereport(request, report_id):
    user = request.user
    logger.debug("user %s, method: %s" % (user, request.method))
    try:
        report = Report.objects.get(id = report_id, creator = user)
        report.delete()
        messages.info(request, f"Your report {report.name} is deleted")
    except Exception as e:
        logger.warning('Cannot remove report id: %s -- %s' % (report_id, e))
        messages.warning(request, "Cannot delete requested report.")
    return redirect('report:list')



urlpatterns = [
    url(r'^newreport/?$', newreport, name = 'new'),
    url(r'^listreport/?$', listreport, name = 'list'),
    url(r'^openreport/(?P<report_id>\d+)$', openreport, name = 'openreport'),
    url(r'^deletereport/(?P<report_id>\d+)$', deletereport, name = 'deletereport'), 
 ]
