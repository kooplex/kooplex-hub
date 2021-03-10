import logging
import re

from django.db import models
from django.conf.urls import url
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import redirect, render
from django_tables2 import RequestConfig
from django.views.generic import ListView, CreateView, UpdateView
from django.urls import reverse_lazy

from hub.models import Image, Project, UserProjectBinding
from hub.models import Report, ReportServiceBinding, Service
from hub.forms import FormReport

from kooplex.lib import now, translate_date, custom_redirect
from kooplex.settings import KOOPLEX
from kooplex.lib.filesystem import recreate_report


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
            scope = request.POST['scope']
            pfi = request.POST['index_selector']
            if pfi.count(',') != 2:
                messages.error(request, f'Report {name} is not created. Make sure there is no comma (,) in file or folder name.')
                return redirect('report:list')
            _, project_id, folder, index, _ = re.split(r'^\((\d+),([^,]+),([^,]+)\)$', pfi)
            project = Project.objects.get(id = project_id)
            try:
                prev_report = Report.objects.get(name = name, creator = user, project = project)
                prev_report.delete()
                logger.debug(f'Previous report {name} removed')
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
                scope = scope,
                password = request.POST['password'] if 'password' in request.POST else '',
            )
            messages.info(request, f'Report {name} is created')
            return redirect('report:list')
        except Exception as e:
            logger.error(e)
            raise
    else:
        return redirect('report:list')


@login_required
def refreshreport(request, report_id):
    """Recreates report."""
    user = request.user
    logger.debug("user %s, method: %s" % (user, request.method))
    try:
        report = Report.objects.get(id = report_id)
        UserProjectBinding.objects.get(user = user, project = report.project)
        recreate_report(report)
        messages.info(request, f"Report {report.name} is recreated")
        ev = report.service.restart()
        if ev.wait(timeout = 10):
            messages.info(request, f'Service {report.service.name} is restarted.')
        else:
            messages.warning(request, f'Service {report.service.name} did not start within 10 seconds, wait some time.')
    except UserProjectBinding.DoesNotExist:
        logger.error(f'Permission denied {user} tries to recreate report {report.name}')
        messages.error(request, "You do not have permission to recreate report {report.name}")
    except Exception as e:
        logger.error(f'Cannot fully recreate report -- {e}')
        messages.error(request, f'Some problems occured -- {e}')
    return redirect('report:list')


#@login_required
def listreport(request):
    """Renders new report list."""
    user = request.user
    search = request.POST.get('button', '') == 'search'
    logger.debug("user %s, method: %s" % (user, request.method))
    listing = request.method == 'GET' or (request.method == 'POST' and search)
    if not listing:
        return redirect('report:list')
    Q = models.Q
    if user.is_authenticated:
        projects = [ upb.project for upb in UserProjectBinding.objects.filter(user = user) ]
        reports = Report.objects.filter(Q(scope__in = [ Report.SC_PUBLIC, Report.SC_INTERNAL ]) | Q(scope = Report.SC_PRIVATE, project__in = projects))
        pattern = request.POST.get('report_or_creator', user.search.report_list)
        if pattern:
            reports = reports.filter(Q(name__icontains = pattern) | models.Q(creator__first_name__icontains = pattern) | Q(creator__last_name__icontains = pattern) | Q(creator__username__icontains = pattern))
        if len(reports) and pattern != user.search.report_list:
            user.search.report_list = pattern
            user.search.save()
    else:
        reports = Report.objects.filter(scope = Report.SC_PUBLIC)

    context_dict = {
        'menu_report': 'active',
        'next_page': 'indexpage', 
        'reports' : reports,
    }
    return render(request, 'report/list.html', context = context_dict)

#@login_required
def openreport(request, report_id):
    """Opens report pod/container."""
    user = request.user
    logger.debug("user %s, method: %s" % (user, request.method))
    try:
        report = Report.objects.get(id = report_id)
        environment = report.service
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


@login_required
def layoutflip(request):
    from hub.models import Layout
    if hasattr(request.user, 'layout'):
        l = request.user.layout
        l.report_list = not l.report_list
        l.save()
    else:
        Layout.objects.create(user = request.user)
    return redirect('report:list')


urlpatterns = [
    url(r'^newreport/?$', newreport, name = 'new'),
    url(r'^refreshreport/(?P<report_id>\d+)$', refreshreport, name = 'refresh'),
    url(r'^listreport/?$', listreport, name = 'list'),
    url(r'^searchreport/?$', listreport, name = 'l_search'),
    url(r'^openreport/(?P<report_id>\d+)$', openreport, name = 'openreport'),
    url(r'^deletereport/(?P<report_id>\d+)$', deletereport, name = 'deletereport'), 
    url(r'^layoutflip/?$', layoutflip, name = 'layout_flip'), 
 ]
