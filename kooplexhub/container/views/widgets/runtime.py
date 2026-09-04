from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse

from ..mixins import ContainerAccessMixin
from ...services.runtime_presenter import ContainerRuntimePresenter


class ContainerRuntimePartialView(
    LoginRequiredMixin,
    ContainerAccessMixin,
    TemplateView,
):
    def get(
        self,
        request,
        *args,
        **kwargs,
    ):
        self.container = (
            self.get_container_queryset()
            .filter(pk=kwargs["pk"])
            .first()
        )

        if self.container is None:
            return HttpResponse(status=204)

        return super().get(
            request,
            *args,
            **kwargs,
        )

    def get_context_data(
        self,
        **kwargs,
    ):
        context = super().get_context_data(
            **kwargs
        )

        container = self.container

        context.update({
            "container": container,
            "runtime":
                ContainerRuntimePresenter(
                    container
                ),
        })

        return context


class ContainerStartButtonPartialView(ContainerRuntimePartialView):
    template_name = "container/partials/widgets/start_button.html"


class ContainerStopButtonPartialView(ContainerRuntimePartialView):
    template_name = "container/partials/widgets/stop_button.html"


class ContainerRestartButtonPartialView(ContainerRuntimePartialView):
    template_name = "container/partials/widgets/restart_button.html"


class ContainerFetchlogButtonPartialView(ContainerRuntimePartialView):
    template_name = "container/partials/widgets/fetchlog_button.html"

class ContainerBackendStatusPartialView(ContainerRuntimePartialView):
    template_name = "container/partials/widgets/backend_status.html"

