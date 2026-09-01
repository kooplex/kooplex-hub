from decimal import Decimal

from django import forms

from ..services.image_catalog import (
    ImageCatalogService,
)
from ..models import (
    Image,
)
from container.conf import (
    CONTAINER_SETTINGS,
)



class ContainerCreateForm(forms.Form):
    name = forms.CharField(
            max_length=200,
            min_length=3,
        )

    image = forms.ModelChoiceField(
        queryset=Image.objects.none(),
        required=True,
    )

    cpu_cores = forms.DecimalField(
        required=False,
        min_value=Decimal("0"),
        decimal_places=2,
        max_digits=6,
    )

    memory_gib = forms.DecimalField(
        required=False,
        min_value=Decimal("0"),
        decimal_places=2,
        max_digits=6,
    )

    gpu_count = forms.IntegerField(
        required=False,
        min_value=0,
    )


    def __init__(
        self, 
        *args, 
        user, 
        **kwargs
    ):
        super().__init__(*args, **kwargs)

        self.fields["image"].queryset = (
            ImageCatalogService
            .available_for_user(user=user)
        )

        resources = (
            CONTAINER_SETTINGS
            .kubernetes
            .resources
        )

        self.fields["cpu_cores"].widget.attrs[
            "placeholder"
        ] = f"{resources.default_cpu_m / 1000:g}"
        
        self.fields["memory_gib"].widget.attrs[
            "placeholder"
        ] = f"{resources.default_memory_mib / 1024:g}"
        
        self.fields["gpu_count"].widget.attrs[
            "placeholder"
        ] = str(
            resources.default_gpu
        )

    def clean_name(self):
        return (
            self.cleaned_data["name"]
            .strip()
        )

    def clean(self):
        cleaned = super().clean()

        resources = (
            CONTAINER_SETTINGS
            .kubernetes
            .resources
        )

        cpu_cores = cleaned.get("cpu_cores")

        if cpu_cores is None:
            cpu_m = resources.default_cpu_m
        else:
            cpu_m = int(
                cpu_cores * Decimal("1000")
            )

        if cpu_m < resources.min_cpu_m:
            self.add_error(
                "cpu_cores",
                (
                    "CPU must be at least "
                    f"{resources.min_cpu_m / 1000:g} "
                    "cores."
                ),
            )

        memory_gib = cleaned.get(
            "memory_gib"
        )
        
        if memory_gib is None:
            memory_mib = (
                resources.default_memory_mib
            )
        else:
            memory_mib = int(
                memory_gib * Decimal("1024")
            )
        
        gpu_count = cleaned.get(
            "gpu_count"
        )
        
        if gpu_count is None:
            gpu_count = resources.default_gpu

        if (
            resources.max_cpu_m is not None
            and cpu_m > resources.max_cpu_m
        ):
            self.add_error(
                "cpu_cores",
                (
                    "CPU may not exceed "
                    f"{resources.max_cpu_m / 1000:g} "
                    "cores."
                ),
            )

        if (
            memory_mib
            < resources.min_memory_mib
        ):
            self.add_error(
                "memory_gib",
                (
                    "Memory must be at least "
                    f"{resources.min_memory_mib / 1024:g} "
                    "GiB."
                ),
            )

        if (
            resources.max_memory_mib
            is not None
            and memory_mib
            > resources.max_memory_mib
        ):
            self.add_error(
                "memory_gib",
                (
                    "Memory may not exceed "
                    f"{resources.max_memory_mib / 1024:g} "
                    "GiB."
                ),
            )

        if (
            resources.max_gpu is not None
            and gpu_count
            > resources.max_gpu
        ):
            self.add_error(
                "gpu_count",
                (
                    "GPU count may not exceed "
                    f"{resources.max_gpu}."
                ),
            )

        cleaned[
            "requested_cpu_m"
        ] = cpu_m

        cleaned[
            "requested_memory_mib"
        ] = memory_mib

        cleaned[
            "requested_gpu"
        ] = gpu_count

        return cleaned


