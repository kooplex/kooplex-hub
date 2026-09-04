from django import forms

from ..conf import CONTAINER_SETTINGS
from ..models import Container
from ..services.image_catalog import ImageCatalogService
from ..services.compute_limits import compute_limits_provider
from ..services.compute_resolver import resolve_container_resources


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


class ContainerImageForm(ContainerWidgetForm):
    class Meta(ContainerWidgetForm.Meta):
        fields = ["image"]

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["image"].queryset = (
            ImageCatalogService.available_for_user(
                user=user,
            )
        )


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

        if self.instance.requested_uptime_hours is None:
            self.initial["requested_uptime_hours"] = (
                limits.default_idletime
            )

    def clean_requested_uptime_hours(self):
        if self.data.get("requested_uptime_hours_use_default") == "1":
            return None

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
            "limit_cpu_m",
            "requested_memory_mib",
            "limit_memory_mib",
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

        for name in (
            "requested_cpu_m",
            "limit_cpu_m",
        ):
            self.fields[name].widget = forms.NumberInput(
                attrs={
                    "type": "range",
                    "min": limits.cpu_min,
                    "max": limits.cpu_max,
                    "step": limits.cpu_step,
                    "class": "form-range",
                }
            )

        for name in (
            "requested_memory_mib",
            "limit_memory_mib",
        ):
            self.fields[name].widget = forms.NumberInput(
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

        resources = CONTAINER_SETTINGS.kubernetes.resources
        
        resolved = resolve_container_resources(
            self.instance,
            resources,
        )
        
        if self.instance.requested_cpu_m is None:
            self.initial["requested_cpu_m"] = resolved.cpu_request_m
        
        if self.instance.limit_cpu_m is None:
            self.initial["limit_cpu_m"] = resolved.cpu_limit_m
        
        if self.instance.requested_memory_mib is None:
            self.initial["requested_memory_mib"] = resolved.memory_request_mib
        
        if self.instance.limit_memory_mib is None:
            self.initial["limit_memory_mib"] = resolved.memory_limit_mib
        
        if self.instance.requested_gpu is None:
            self.initial["requested_gpu"] = resolved.gpu

        if limits.gpu_max <= 0:
            self.fields.pop("requested_gpu", None)

    def _apply_default_flag(self, cleaned, field_name):
        flag_name = f"{field_name}_use_default"
    
        if self.data.get(flag_name) == "1":
            cleaned[field_name] = None

    def clean(self):
        cleaned = super().clean()

        for field_name in (
            "requested_cpu_m",
            "limit_cpu_m",
            "requested_memory_mib",
            "limit_memory_mib",
            "requested_gpu",
        ):
            self._apply_default_flag(cleaned, field_name)
    
        if (
            cleaned.get("requested_cpu_m") is None
            and cleaned.get("limit_cpu_m") is not None
        ):
            cleaned["limit_cpu_m"] = None
    
        if (
            cleaned.get("requested_memory_mib") is None
            and cleaned.get("limit_memory_mib") is not None
        ):
            cleaned["limit_memory_mib"] = None

        cpu_request = cleaned.get("requested_cpu_m")
        cpu_limit = cleaned.get("limit_cpu_m")
    
        if (
            cpu_request is not None
            and cpu_limit is not None
            and cpu_request > cpu_limit
        ):
            self.add_error(
                "limit_cpu_m",
                "CPU limit must be greater than or equal to request.",
            )
    
        memory_request = cleaned.get("requested_memory_mib")
        memory_limit = cleaned.get("limit_memory_mib")
    
        if (
            memory_request is not None
            and memory_limit is not None
            and memory_request > memory_limit
        ):
            self.add_error(
                "limit_memory_mib",
                "Memory limit must be greater than or equal to request.",
            )
    
        return cleaned


