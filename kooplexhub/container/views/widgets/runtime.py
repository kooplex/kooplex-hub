from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404

from ..mixins import ContainerAccessMixin
from ...services.runtime_presenter import ContainerRuntimePresenter


class ContainerRuntimePartialView(
    LoginRequiredMixin,
    ContainerAccessMixin,
    TemplateView,
):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        container = self.get_container()
        context.update(
            {
                "container": container,
                "runtime": ContainerRuntimePresenter(container),
            }
        )
        return context


class ContainerStartButtonPartialView(ContainerRuntimePartialView):
    template_name = "container/partials/widgets/start_button.html"


class ContainerStopButtonPartialView(ContainerRuntimePartialView):
    template_name = "container/partials/widgets/stop_button.html"


class ContainerRestartButtonPartialView(ContainerRuntimePartialView):
    template_name = "container/partials/widgets/restart_button.html"


class ContainerFetchlogButtonPartialView(ContainerRuntimePartialView):
    template_name = "container/partials/widgets/fetchlog_button.html"


