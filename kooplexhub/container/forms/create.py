from django import forms

from ..models import (
    Container, 
    Image,
)


class ContainerCreateForm(forms.ModelForm):
    image = forms.ModelChoiceField(
        queryset=Image.objects.none(),
        required=True,
    )

    class Meta:
        model = Container
        fields = ["name", "image"]

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

        self.fields["image"].queryset = Image.objects.filter(
            imagetype=Image.ImageType.PROJECT,
            present=True,
        )

    def clean_name(self):
        name = self.cleaned_data["name"].strip()

        if len(name) < 3:
            raise forms.ValidationError("Name must be at least 3 characters.")

        return name

    def save(self, commit=True):
        container = super().save(commit=False)
        container.user = self.user

        # Set other safe defaults here if your model requires them.
        # container.status = Container.Status.CREATED
        # container.cpu = ...
        # container.memory = ...

        if commit:
            container.save()
            self.save_m2m()

        return container


