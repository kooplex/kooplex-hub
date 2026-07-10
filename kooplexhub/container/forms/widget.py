from django import forms

from ..models import Container


class ContainerNameForm(forms.ModelForm):
    class Meta:
        model = Container
        fields = ["name"]

    def clean_name(self):
        name = self.cleaned_data["name"].strip()

        if len(name) < 3:
            raise forms.ValidationError("Name must be at least 3 characters.")

        return name


class ContainerUptimeForm(forms.ModelForm):
    class Meta:
        model = Container
        fields = ["requested_uptime_hours"]
