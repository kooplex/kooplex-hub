from django import forms

from ..conf import CONTAINER_SETTINGS
from ..models import Container
from ..services.compute_limits import compute_limits_provider


class ContainerWidgetForm(forms.ModelForm):
    class Meta:
        model = Container
        fields = []


class ContainerNameForm(ContainerWidgetForm):
    class Meta(ContainerWidgetForm.Meta):
        fields = ["name"]

    def clean_name(self):
        name = self.cleaned_data["name"].strip()

        if len(name) < 3:
            raise forms.ValidationError(
                "Name must be at least 3 characters."
            )

        return name


class ContainerUptimeForm(ContainerWidgetForm):
    class Meta(ContainerWidgetForm.Meta):
        fields = [
            "requested_uptime_hours",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        limits = CONTAINER_SETTINGS.kubernetes.resources

        self.fields[
            "requested_uptime_hours"
        ].widget = forms.NumberInput(
            attrs={
                "type": "range",
                "min": limits.min_idletime,
                "max": limits.max_idletime,
                "step": 1,
                "class": "form-range",
            }
        )

    def clean_requested_uptime_hours(self):
        value = self.cleaned_data[
            "requested_uptime_hours"
        ]

        limits = CONTAINER_SETTINGS.kubernetes.resources

        if not (
            limits.min_idletime
            <= value
            <= limits.max_idletime
        ):
            raise forms.ValidationError(
                f"Must be between "
                f"{limits.min_idletime} and "
                f"{limits.max_idletime} hours."
            )

        return value


class ContainerComputeForm(ContainerWidgetForm):
    class Meta(ContainerWidgetForm.Meta):
        fields = [
            "requested_cpu_m",
            "requested_memory_mib",
            "requested_gpu",
        ]

    def __init__(
        self,
        *args,
        limits,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        self.limits = limits

        self.fields[
            "requested_cpu_m"
        ].widget = forms.NumberInput(
            attrs={
                "type": "range",
                "min": limits.cpu_min,
                "max": limits.cpu_max,
                "step": limits.cpu_step,
                "class": "form-range",
            }
        )

        self.fields[
            "requested_memory_mib"
        ].widget = forms.NumberInput(
            attrs={
                "type": "range",
                "min": limits.memory_min,
                "max": limits.memory_max,
                "step": limits.memory_step,
                "class": "form-range",
            }
        )

        self.fields[
            "requested_gpu"
        ].widget = forms.NumberInput(
            attrs={
                "type": "range",
                "min": limits.gpu_min,
                "max": limits.gpu_max,
                "step": limits.gpu_step,
                "class": "form-range",
            }
        )

    def clean_requested_cpu_m(self):
        value = self.cleaned_data["requested_cpu_m"]

        if not (
            self.limits.cpu_min
            <= value
            <= self.limits.cpu_max
        ):
            raise forms.ValidationError(
                f"CPU must be between "
                f"{self.limits.cpu_min} and "
                f"{self.limits.cpu_max}."
            )

        return value

    def clean_requested_memory_mib(self):
        value = self.cleaned_data[
            "requested_memory_mib"
        ]

        if not (
            self.limits.memory_min
            <= value
            <= self.limits.memory_max
        ):
            raise forms.ValidationError(
                f"Memory must be between "
                f"{self.limits.memory_min} and "
                f"{self.limits.memory_max}."
            )

        return value

    def clean_requested_gpu(self):
        value = self.cleaned_data["requested_gpu"]

        if not (
            self.limits.gpu_min
            <= value
            <= self.limits.gpu_max
        ):
            raise forms.ValidationError(
                f"GPU must be between "
                f"{self.limits.gpu_min} and "
                f"{self.limits.gpu_max}."
            )

        return value


