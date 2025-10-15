from django.views import generic
from django.contrib.auth.mixins import AccessMixin
from .models.token import Token
from container.lib.cluster_resources_api import *

from .conf import HUB_SETTINGS


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

