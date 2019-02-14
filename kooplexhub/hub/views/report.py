import logging

from django.db import transaction
from django.conf.urls import url
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import redirect, render
from django_tables2 import RequestConfig


from hub.models import Report
from hub.forms import FormReport

from kooplex.lib import now, translate_date
from kooplex.settings import KOOPLEX

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
            index = request.POST['index'] if reporttype != Report.TP_BOKEH else ''
            Report.objects.create(
                name = request.POST['name'],
                creator = user,
                description = request.POST['description'], 
                reporttype = reporttype,
                index = index,
                folder = request.POST['folder'],
                password = request.POST['password'],
            )
            messages.info(request, "Report %s is created" % request.POST['name'])
            return redirect('report:list')
        except Exception as e:
            logger.error(e)
            raise
    else:
        return redirect('indexpage')


@login_required
def listreport(request):#, next_page):
    """Renders new report list."""
    user = request.user
    logger.debug("user %s, method: %s" % (user, request.method))
    context_dict = {
        'menu_report': 'active',
        'next_page': 'indexpage', #next_page,
    }
    return render(request, 'report/list.html', context = context_dict)


@login_required
def openreport(request, report_id):
    """Renders new report list."""
    user = request.user
    logger.debug("user %s, method: %s" % (user, request.method))
    try:
        report = Report.objects.get(id = report_id)
    except Exception as e:
        logger.warning('Cannot resolve report id: %s -- %s' % (report_id, e))
        return redirect('indexpage')
    url_external = report.url_external
    logger.debug('redirect: %s' % url_external)
    return redirect(url_external)


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
    url(r'^openreport/(?P<report_id>\d+)$', openreport, name = 'openreport'),
    url(r'^deletereport/(?P<report_id>\d+)$', deletereport, name = 'deletereport'), 
]
