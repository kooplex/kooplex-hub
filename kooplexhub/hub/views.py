from django.views import generic
from django.contrib.auth.mixins import AccessMixin
from kooplexhub import settings
from .models.token import Token
from django.shortcuts import render
import pandas
from numpy import arange
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
from container.lib.cluster_resources_api import *

from .conf import HUB_SETTINGS

class IndexView(AccessMixin, generic.TemplateView):
    template_name = 'index_unauthorized.html'
    context_object_name = 'indexpage'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['url_login'] = settings.LOGIN_URL
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

class UserTokenView(AccessMixin, generic.TemplateView):
    template_name = 'usertokens.html'
    context_object_name = 'usertokens'

    def get_context_data(self, **kwargs):
        from hub.models import TokenType
        context = super().get_context_data(**kwargs)
        user_tokens=Token.objects.filter(user=self.request.user)
        context['tokens'] = user_tokens
        context['tokentypes']=TokenType.objects.all().exclude(id__in=[ t.type.id for t in user_tokens])
        context['wss_token_config'] = HUB_SETTINGS['wss']['token'].format(user = self.request.user)
        context['wss_resources'] = HUB_SETTINGS['wss']['resources'].format(user = self.request.user)
        return context

