from django import forms
from ..models import Volume


class VolumeDescriptionForm(forms.ModelForm):
    class Meta:
        model = Volume
        fields = ("description",)
        widgets = {"description": forms.Textarea(attrs={"class": "form-control", "rows": 4})}


class VolumeScopeForm(forms.ModelForm):
    class Meta:
        model = Volume
        fields = ("scope",)

    scope = forms.ChoiceField(choices=Volume.Scope.choices[:3])
