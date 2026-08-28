from django import forms

from ..services.image_catalog import (
    ImageCatalogService,
)
from ..models import (
    Image,
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

    def clean_name(self):
        return self.cleaned_data["name"].strip()


