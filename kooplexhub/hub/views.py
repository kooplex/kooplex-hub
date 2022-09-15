from django.views import generic
from django.contrib.auth.mixins import AccessMixin
from kooplexhub import settings

class IndexView(AccessMixin, generic.TemplateView):
    template_name = 'index_unauthorized.html'
    context_object_name = 'indexpage'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['url_profile'] = settings.URL_ACCOUNTS_PROFILE
        return context

    def setup(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            self.template_name = 'index.html'
        super().setup(request, *args, **kwargs)

class MonitoringView(AccessMixin, generic.TemplateView):
    template_name = 'monitoring.html'
    context_object_name = 'monitoring'

class MonitoringDashboardView(AccessMixin, generic.TemplateView):
    template_name = 'monitoring_dashboard.html'
    context_object_name = 'monitoring'

#TEST TASK

from django.shortcuts import redirect
import logging
import time
from kooplexhub.tasks import task_do_something
logger = logging.getLogger(__name__)

def task(request, duma):
    logger.info("DEFINE TASK")
    a = task_do_something.delay(duma)
    logger.info(a)
    return redirect('indexpage')

