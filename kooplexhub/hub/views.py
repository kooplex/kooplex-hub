from django.views import generic
from django.contrib.auth.mixins import AccessMixin
from django.contrib.auth.views import LogoutView
from django.shortcuts import redirect

from .models import (
    Note,
)

from .models.token import Token #???
#from container.lib.cluster_resources_api import *

from .conf import HUB_SETTINGS
from kooplexhub.settings import URL_AUTH

class OAuthLogoutView(LogoutView):
    def get(self, request, *args, **kwargs):
        super().get(request, *args, **kwargs)
        return redirect(
            f"{URL_AUTH}/accounts/logout/"
        )

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


class NotesFooterView(
    generic.TemplateView,
):
    template_name = (
        "hub/partials/notes_footer.html"
    )

    def get_context_data(
        self,
        **kwargs,
    ):
        context = (
            super().get_context_data(**kwargs)
        )

        context["notes"] = (
            Note.objects.visible_to(
                self.request.user
            )
        )

        return context


