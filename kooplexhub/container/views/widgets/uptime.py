from django.views.generic import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render

from ..mixins import ContainerAccessMixin
from ...services.runtime_presenter import ContainerRuntimePresenter
from ...services.live import broadcast_container_runtime_changed

from ...conf import CONTAINER_SETTINGS


class ContainerUptimeWidgetMixin(ContainerAccessMixin):
    display_template_name = (
        "container/partials/widgets/uptime_display.html"
    )
    edit_template_name = (
        "container/partials/widgets/uptime_edit.html"
    )

    def get_widget_context(self, container, **extra):
        return {
            "container": container,
            "runtime": ContainerRuntimePresenter(container),
            **extra,
        }

    def render_display(self, request, container):
        return render(
            request,
            self.display_template_name,
            self.get_widget_context(container),
        )

    def render_edit(self, request, container, **extra):
        return render(
            request,
            self.edit_template_name,
            self.get_widget_context(container, **extra),
        )


class ContainerUptimeDisplayView(
    LoginRequiredMixin,
    ContainerUptimeWidgetMixin,
    View,
):
    def get(self, request, pk):
        container = self.get_container()
        return self.render_display(request, container)


class ContainerUptimeEditView(
    LoginRequiredMixin,
    ContainerUptimeWidgetMixin,
    View,
):
    def get(self, request, pk):
        container = self.get_container()
        runtime = ContainerRuntimePresenter(container)

        if not runtime.uptime_is_editable:
            return self.render_display(request, container)

        return self.render_edit(request, container)


class ContainerUptimeUpdateView(
    LoginRequiredMixin,
    ContainerUptimeWidgetMixin,
    View,
):
    def post(self, request, pk):
        container = self.get_container()
        runtime = ContainerRuntimePresenter(container)

        if not runtime.uptime_is_editable:
            return self.render_display(request, container)

        raw_value = request.POST.get("requested_uptime_hours")

        try:
            value = int(raw_value)
        except (TypeError, ValueError):
            return self.render_edit(
                request,
                container,
                error="Idle time must be a whole number.",
            )

        resource_settings = (
            CONTAINER_SETTINGS.kubernetes.resources
        )

        minimum = resource_settings.min_idletime
        maximum = resource_settings.max_idletime

        if value < minimum or value > maximum:
            return self.render_edit(
                request,
                container,
                error=(
                    f"Idle time must be between "
                    f"{minimum} and {maximum} hours."
                ),
            )

        if container.requested_uptime_hours != value:
            container.requested_uptime_hours = value
            container.save(
                update_fields=["requested_uptime_hours"]
            )

            broadcast_container_runtime_changed(
                container=container,
                actor=request.user,
                reason="container.idletime.updated",
            )

        container.refresh_from_db()

        return self.render_display(request, container)


