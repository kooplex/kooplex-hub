from django import forms

from ..models import Course
from ..services.names import (
    validate_course_name,
)


class CourseWidgetForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = []


class CourseNameForm(CourseWidgetForm):
    class Meta(CourseWidgetForm.Meta):
        fields = ["name"]

    def clean_name(self):
        exclude_course = None

        if self.instance.pk:
            exclude_course = self.instance

        return validate_course_name(
            name=self.cleaned_data["name"],
            exclude_course=self.instance,
        )


class CourseDescriptionForm(CourseWidgetForm):
    class Meta(CourseWidgetForm.Meta):
        fields = ["description"]

    def clean_description(self) -> str:
        description = self.cleaned_data.get("description") or ""
        description = description.strip()
        if len(description) < 3:
            raise forms.ValidationError(
                "Description must be at least 3 characters."
            )

        return description


