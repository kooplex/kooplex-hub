import json

from .base import (
    ContainerWidgetDisplayView,
    ContainerWidgetEditView,
    ContainerWidgetUpdateView,
)
from ...forms.widgets import ContainerUptimeForm
from ...services.live import (
    broadcast_container_runtime_changed,
)
from ...services.runtime_presenter import (
    ContainerRuntimePresenter,
)

class ContainerUptimeWidgetMixin:
    form_class = ContainerUptimeForm
    display_template_name = "container/partials/widgets/uptime_display.html"
    edit_template_name = "container/partials/widgets/uptime_edit.html"

    def get_display_context(self, container):
        context = super().get_display_context(
            container
        )

        context["runtime"] = (
            ContainerRuntimePresenter(container)
        )

        return context

    def get_edit_context(self, container, form):
        context = super().get_edit_context(
            container,
            form,
        )

        context["runtime"] = (
            ContainerRuntimePresenter(container)
        )

        return context

    def can_edit(self, container):
        return container.state not in {
            container.State.STARTING,
            container.State.STOPPING,
        }


class ContainerUptimeDisplayView(
    ContainerUptimeWidgetMixin,
    ContainerWidgetDisplayView,
):
    pass


class ContainerUptimeEditView(
    ContainerUptimeWidgetMixin,
    ContainerWidgetEditView,
):
    pass


class ContainerUptimeUpdateView(
    ContainerUptimeWidgetMixin,
    ContainerWidgetUpdateView,
):
    def after_save(self, container, form):
        broadcast_container_runtime_changed(
            container=container,
            actor=self.request.user,
            reason="container.idletime.updated",
        )

    def add_success_headers(
        self,
        response,
        container,
        form,
    ):
        response["HX-Trigger"] = json.dumps(
            {
                "kooplex-toast": {
                    "message": (
                        "Idle-time limit updated."
                    ),
                    "level": "success",
                }
            }
        )

        return response
