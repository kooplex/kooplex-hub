from django import forms

from ..conf import CONTAINER_SETTINGS
from ..models import Container
from ..services.compute_limits import compute_limits_provider


class ContainerWidgetForm(forms.ModelForm):
    class Meta:
        model = Container
        fields = []

    def __init__(self, *args, container=None, **kwargs):
        if container is not None:
            kwargs.setdefault("instance", container)
        super().__init__(*args, **kwargs)

    @property
    def container(self):
        return self.instance


class ContainerNameForm(ContainerWidgetForm):
    class Meta(ContainerWidgetForm.Meta):
        fields = ["name"]

    def clean_name(self):
        name = self.cleaned_data["name"].strip()

        if len(name) < 3:
            raise forms.ValidationError("Name must be at least 3 characters.")

        return name


class ContainerUptimeForm(ContainerWidgetForm):
    class Meta(ContainerWidgetForm.Meta):
        fields = ["requested_uptime_hours"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        limits = CONTAINER_SETTINGS.kubernetes.resources
        self.fields["requested_uptime_hours"].widget = forms.NumberInput(
            attrs={
                "type": "range",
                "min": limits.min_idletime,
                "max": limits.max_idletime,
                "step": 1,
                "class": "form-range",
            }
        )

    def clean_requested_uptime_hours(self):
        value = self.cleaned_data["requested_uptime_hours"]
        limits = CONTAINER_SETTINGS.kubernetes.resources

        if not limits.min_idletime <= value <= limits.max_idletime:
            raise forms.ValidationError(
                f"Must be between {limits.min_idletime} and "
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        limits = compute_limits_provider.for_container(self.container)

        self.fields["requested_cpu_m"].widget = forms.NumberInput(
            attrs={
                "type": "range",
                "min": limits.cpu_min,
                "max": limits.cpu_max,
                "step": limits.cpu_step,
                "class": "form-range",
            }
        )

        self.fields["requested_memory_mib"].widget = forms.NumberInput(
            attrs={
                "type": "range",
                "min": limits.memory_min,
                "max": limits.memory_max,
                "step": limits.memory_step,
                "class": "form-range",
            }
        )

        self.fields["requested_gpu"].widget = forms.NumberInput(
            attrs={
                "type": "range",
                "min": limits.gpu_min,
                "max": limits.gpu_max,
                "step": limits.gpu_step,
                "class": "form-range",
            }
        )

        self._limits = limits

    def clean_requested_cpu_m(self):
        value = self.cleaned_data["requested_cpu_m"]

        if not self._limits.cpu_min <= value <= self._limits.cpu_max:
            raise forms.ValidationError(
                f"CPU must be between {self._limits.cpu_min} "
                f"and {self._limits.cpu_max}."
            )

        return value

    def clean_requested_memory_mib(self):
        value = self.cleaned_data["requested_memory_mib"]

        if not self._limits.memory_min <= value <= self._limits.memory_max:
            raise forms.ValidationError(
                f"Memory must be between {self._limits.memory_min} "
                f"and {self._limits.memory_max}."
            )

        return value

    def clean_requested_gpu(self):
        value = self.cleaned_data["requested_gpu"]

        if not self._limits.gpu_min <= value <= self._limits.gpu_max:
            raise forms.ValidationError(
                f"GPU must be between {self._limits.gpu_min} "
                f"and {self._limits.gpu_max}."
            )

        return value


