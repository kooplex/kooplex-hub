from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View

from ..mixins import ContainerAccessMixin
from ...services.compute_presenter import ContainerComputePresenter


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


