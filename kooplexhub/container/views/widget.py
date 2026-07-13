import json
import logging
from decimal import (
    Decimal, 
    InvalidOperation,
)

from django.views.generic import (
    View,
    TemplateView,
)
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import (
    get_object_or_404, 
    render, 
)

from .mixins import (
    ContainerRuntimePartialMixin,
    ContainerAccessMixin,
)
from ..conf import CONTAINER_SETTINGS
from ..services.runtime_presenter import ContainerRuntimePresenter
from ..services.compute_presenter import ContainerComputePresenter
from ..services.compute_limits import compute_limits_provider
from ..services.live import (
    broadcast_container_live_event,
    broadcast_container_runtime_changed,
)
from .mixins import ContainerAccessMixin
from ..models import Container


logger = logging.getLogger(__name__)


class ContainerStartButtonPartialView(
    LoginRequiredMixin,
    ContainerRuntimePartialMixin,
    TemplateView,
):
    template_name = "container/partials/widgets/start_button.html"

    def get_context_data(self, **kwargs):
        container = self.get_container()
        return self.get_context_data_for_container(container)


class ContainerStopButtonPartialView(
    LoginRequiredMixin,
    ContainerRuntimePartialMixin,
    TemplateView,
):
    template_name = "container/partials/widgets/stop_button.html"

    def get_context_data(self, **kwargs):
        container = self.get_container()
        return self.get_context_data_for_container(container)


class ContainerRestartButtonPartialView(
    LoginRequiredMixin,
    TemplateView,
):
    template_name = "container/partials/widgets/restart_button.html"

    def get_context_data(self, **kwargs):
        container = get_object_or_404(
            Container.objects.filter(user=self.request.user),
            pk=self.kwargs["pk"],
        )

        return {
            "container": container,
            "runtime": ContainerRuntimePresenter(container),
        }


class ContainerFetchlogButtonPartialView(
    LoginRequiredMixin,
    ContainerRuntimePartialMixin,
    TemplateView,
):
    template_name = "container/partials/widgets/fetchlog_button.html"

    def get_context_data(self, **kwargs):
        container = self.get_container()
        return self.get_context_data_for_container(container)


class ContainerEditableDisplayView(
    LoginRequiredMixin,
    ContainerAccessMixin,
    View,
):
    template_name = "ui/widgets/editable_text/display.html"
    field_name = None

    def get_value(self, container):
        return getattr(container, self.field_name)

    def get_edit_url(self, container):
        raise NotImplementedError

    def get_dom_id(self, container):
        raise NotImplementedError

    def get(self, request, pk):
        container = self.get_container()

        return render(
            request,
            self.template_name,
            {
                "dom_id": self.get_dom_id(container),
                "value": self.get_value(container),
                "edit_url": self.get_edit_url(container),
            },
        )


class ContainerEditableEditView(
    LoginRequiredMixin,
    ContainerAccessMixin,
    View,
):
    template_name = "ui/widgets/editable_text/form.html"
    field_name = None

    def get_value(self, container):
        return getattr(container, self.field_name)

    def get_update_url(self, container):
        raise NotImplementedError

    def get_cancel_url(self, container):
        raise NotImplementedError

    def get_dom_id(self, container):
        raise NotImplementedError

    def get(self, request, pk):
        container = self.get_container()

        return render(
            request,
            self.template_name,
            {
                "dom_id": self.get_dom_id(container),
                "field_name": self.field_name,
                "value": self.get_value(container),
                "update_url": self.get_update_url(container),
                "cancel_url": self.get_cancel_url(container),
            },
        )


class ContainerEditableUpdateView(
    LoginRequiredMixin,
    ContainerAccessMixin,
    View,
):
    field_name = None
    display_template_name = "ui/widgets/editable_text/display.html"

    def clean_value(self, raw_value):
        return raw_value

    def get_edit_url(self, container):
        raise NotImplementedError

    def get_dom_id(self, container):
        raise NotImplementedError

    def post(self, request, pk):
        container = self.get_container()

        raw_value = request.POST.get(self.field_name)

        if raw_value is None:
            return HttpResponseBadRequest(
                f"Missing field: {self.field_name}"
            )

        value = self.clean_value(raw_value)

        setattr(container, self.field_name, value)
        container.save(update_fields=[self.field_name])

        return render(
            request,
            self.display_template_name,
            {
                "dom_id": self.get_dom_id(container),
                "value": value,
                "edit_url": self.get_edit_url(container),
            },
        )


class ContainerNameDisplayView(ContainerEditableDisplayView):
    field_name = "name"

    def get_dom_id(self, container):
        return container.name_dom_id

    def get_edit_url(self, container):
        return container.name_edit_url


class ContainerNameEditView(ContainerEditableEditView):
    field_name = "name"

    def get_dom_id(self, container):
        return container.name_dom_id

    def get_update_url(self, container):
        return container.name_update_url

    def get_cancel_url(self, container):
        return container.name_display_url


class ContainerNameUpdateView(ContainerEditableUpdateView):
    field_name = "name"

    def clean_value(self, raw_value):
        value = raw_value.strip()

        if len(value) < 3:
            raise ValueError("Name must be at least 3 characters.")

        return value

    def get_dom_id(self, container):
        return container.name_dom_id

    def get_edit_url(self, container):
        return container.name_edit_url


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


class ContainerComputeWidgetMixin(ContainerAccessMixin):
    display_template_name = (
        "container/partials/widgets/compute_display.html"
    )
    edit_template_name = (
        "container/partials/widgets/compute_edit.html"
    )

    def get_compute(self, container):
        limits = compute_limits_provider.for_container(container)

        return ContainerComputePresenter(
            container=container,
            limits=limits,
        )

    def render_display(self, request, container):
        return render(
            request,
            self.display_template_name,
            {
                "container": container,
                "compute": self.get_compute(container),
            },
        )

    def render_edit(self, request, container, errors=None):
        return render(
            request,
            self.edit_template_name,
            {
                "container": container,
                "compute": self.get_compute(container),
                "errors": errors or [],
            },
        )


class ContainerComputeDisplayView(
    LoginRequiredMixin,
    ContainerComputeWidgetMixin,
    View,
):
    def get(self, request, pk):
        return self.render_display(
            request,
            self.get_container(),
        )


class ContainerComputeEditView(
    LoginRequiredMixin,
    ContainerComputeWidgetMixin,
    View,
):
    def get(self, request, pk):
        container = self.get_container()
        compute = self.get_compute(container)

        if not compute.is_editable:
            return self.render_display(request, container)

        return self.render_edit(request, container)


class ContainerComputeUpdateView(
    LoginRequiredMixin,
    ContainerComputeWidgetMixin,
    View,
):
    def post(self, request, pk):
        container = self.get_container()
        compute = self.get_compute(container)

        if not compute.is_editable:
            return self.render_display(request, container)

        values, errors = self.validate_values(
            request=request,
            compute=compute,
        )

        if errors:
            return self.render_edit(
                request,
                container,
                errors=errors,
            )

        changed_fields = []

        for field_name, value in values.items():
            if getattr(container, field_name) != value:
                setattr(container, field_name, value)
                changed_fields.append(field_name)

        restart_marked = False

        if changed_fields:
            container.save(update_fields=changed_fields)

            restart_marked = container.mark_restart(
                "Compute resources changed: "
                + ", ".join(changed_fields),
                save=True,
            )

            broadcast_container_runtime_changed(
                container=container,
                actor=request.user,
                reason="container.compute.updated",
            )

            broadcast_container_live_event(
                user=request.user,
                keys=[
                    f"container:{container.pk}",
                ],
                payload={
                    "event": "container.config.changed",
                    "model": "container",
                    "id": container.pk,
                },
            )

        container.refresh_from_db()

        response = self.render_display(request, container)

        if changed_fields:
            message = "Compute resource request updated."

            if restart_marked:
                message += " Restart required."

            response["HX-Trigger"] = json.dumps(
                {
                    "kooplex-toast": {
                        "message": message,
                        "level": (
                            "warning"
                            if restart_marked
                            else "success"
                        ),
                    }
                }
            )

        return response

    def validate_values(self, request, compute):
        errors = []
        limits = compute.limits

        cpu = self.parse_decimal(
            request.POST.get("requested_cpu_m"),
            "CPU",
            errors,
        )
        memory = self.parse_decimal(
            request.POST.get("requested_memory_mib"),
            "Memory",
            errors,
        )
        gpu = self.parse_integer(
            request.POST.get("requested_gpu"),
            "GPU",
            errors,
        )

        if cpu is not None and not limits.cpu_min <= cpu <= limits.cpu_max:
            errors.append(
                f"CPU must be between "
                f"{limits.cpu_min} and {limits.cpu_max}."
            )

        if (
            memory is not None
            and not limits.memory_min <= memory <= limits.memory_max
        ):
            errors.append(
                f"Memory must be between "
                f"{limits.memory_min} and {limits.memory_max}."
            )

        if gpu is not None and not limits.gpu_min <= gpu <= limits.gpu_max:
            errors.append(
                f"GPU must be between "
                f"{limits.gpu_min} and {limits.gpu_max}."
            )

        return (
            {
                "requested_cpu_m": cpu,
                "requested_memory_mib": memory,
                "requested_gpu": gpu,
            },
            errors,
        )

    @staticmethod
    def parse_decimal(raw_value, label, errors):
        try:
            return Decimal(raw_value)
        except (InvalidOperation, TypeError):
            errors.append(f"{label} must be numeric.")
            return None

    @staticmethod
    def parse_integer(raw_value, label, errors):
        try:
            return int(raw_value)
        except (TypeError, ValueError):
            errors.append(f"{label} must be a whole number.")
            return None


class ContainerOpenButtonPartialView(
    LoginRequiredMixin,
    ContainerAccessMixin,
    TemplateView,
):
    template_name = "container/partials/widgets/open_service_button.html"

    def get_context_data(self, **kwargs):
        container = self.get_container()

        return {
            "container": container,
            "runtime": ContainerRuntimePresenter(container),
            "service_views": list(container.views),
        }
