from django import forms

from ..models import Project


class ProjectJoinForm(forms.Form):
    project = forms.ModelChoiceField(
        queryset=Project.objects.none(),
        required=True,
        empty_label=None,
    )

    def __init__(
        self,
        *args,
        actor,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        self.actor = actor
        self.fields["project"].queryset = (
            Project.objects.joinable_by(actor)
        )



