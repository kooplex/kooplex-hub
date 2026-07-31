from django import forms

from ..models import Project
from ..services.names import (
    validate_project_name_for_creator,
)


class ProjectWidgetForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = []


class ProjectNameForm(ProjectWidgetForm):
    class Meta(ProjectWidgetForm.Meta):
        fields = ["name"]

    def __init__(
        self,
        *args,
        creator,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.creator = creator

    def clean_name(self):
        exclude_project = None

        if self.instance.pk:
            exclude_project = self.instance

        return validate_project_name_for_creator(
            creator=self.creator,
            name=self.cleaned_data["name"],
            exclude_project=self.instance,
        )


class ProjectDescriptionForm(ProjectWidgetForm):
    class Meta(ProjectWidgetForm.Meta):
        fields = ["description"]

    def clean_description(self) -> str:
        description = self.cleaned_data.get("description") or ""
        description = description.strip()
        if len(description) < 3:
            raise forms.ValidationError(
                "Description must be at least 3 characters."
            )

        return description



