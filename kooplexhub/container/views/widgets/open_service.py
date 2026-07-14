from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404

from .runtime import ContainerRuntimePartialView


class ContainerOpenButtonPartialView(ContainerRuntimePartialView):
    template_name = "container/partials/widgets/open_service_button.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        container = context["container"]
        context["service_views"] = list(container.views)
        return context
