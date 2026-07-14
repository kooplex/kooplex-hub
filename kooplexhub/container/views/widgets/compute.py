import json

from .base import (
    ContainerWidgetDisplayView,
    ContainerWidgetEditView,
    ContainerWidgetUpdateView,
)
from ...forms.widgets import ContainerComputeForm
from ...services.compute_limits import (
    compute_limits_provider,
)
from ...services.compute_presenter import (
    ContainerComputePresenter,
)
from ...services.live import (
    broadcast_container_live_event,
    broadcast_container_runtime_changed,
)


class ContainerComputeWidgetMixin:
    form_class = ContainerComputeForm

    display_template_name = (
        "container/partials/widgets/"
        "compute_display.html"
    )

    edit_template_name = (
        "container/partials/widgets/"
        "compute_edit.html"
    )

    def get_form_kwargs(self, container):
        kwargs = super().get_form_kwargs(
            container
        )

        kwargs["limits"] = (
            compute_limits_provider
            .for_container(container)
        )

        return kwargs

    def get_compute(self, container):
        return ContainerComputePresenter(
            container=container,
            limits=(
                compute_limits_provider
                .for_container(container)
            ),
        )

    def get_display_context(self, container):
        context = super().get_display_context(
            container
        )

        context["compute"] = (
            self.get_compute(container)
        )

        return context

    def get_edit_context(self, container, form):
        context = super().get_edit_context(
            container,
            form,
        )

        context["compute"] = (
            self.get_compute(container)
        )

        return context

    def can_edit(self, container):
        return container.state not in {
            container.State.STARTING,
            container.State.STOPPING,
        }


class ContainerComputeDisplayView(
    ContainerComputeWidgetMixin,
    ContainerWidgetDisplayView,
):
    pass


class ContainerComputeEditView(
    ContainerComputeWidgetMixin,
    ContainerWidgetEditView,
):
    pass


class ContainerComputeUpdateView(
    ContainerComputeWidgetMixin,
    ContainerWidgetUpdateView,
):
    def after_save(self, container, form):
        restart_marked = container.mark_restart(
            "Compute resources changed: "
            + ", ".join(form.changed_data),
            save=True,
        )

        self.restart_marked = restart_marked

        broadcast_container_runtime_changed(
            container=container,
            actor=self.request.user,
            reason="container.compute.updated",
        )

        broadcast_container_live_event(
            user=self.request.user,
            keys=[
                f"container:{container.pk}",
            ],
            payload={
                "event": (
                    "container.config.changed"
                ),
                "model": "container",
                "id": container.pk,
            },
        )

    def add_success_headers(
        self,
        response,
        container,
        form,
    ):
        message = (
            "Compute resource request updated."
        )

        if getattr(
            self,
            "restart_marked",
            False,
        ):
            message += " Restart required."

        response["HX-Trigger"] = json.dumps(
            {
                "kooplex-toast": {
                    "message": message,
                    "level": (
                        "warning"
                        if getattr(
                            self,
                            "restart_marked",
                            False,
                        )
                        else "success"
                    ),
                }
            }
        )

        return response

