from django import forms


class AssignmentScheduleForm(forms.Form):
    field = forms.ChoiceField(
        choices=(
            ("valid_from", "Valid from"),
            ("expires_at", "Expires at"),
        )
    )

    valid_from = forms.DateTimeField(
        required=False,
        input_formats=[
            "%Y-%m-%dT%H:%M",
        ],
    )

    expires_at = forms.DateTimeField(
        required=False,
        input_formats=[
            "%Y-%m-%dT%H:%M",
        ],
    )

class AssignmentCreateForm(forms.Form):
    MODE_CREATE = "assignment"
    MODE_CREATE_AND_HANDOUT = "assignment_and_handout"

    creation_mode = forms.ChoiceField(
        choices=(
            (MODE_CREATE, "Create assignment"),
            (
                MODE_CREATE_AND_HANDOUT,
                "Create assignment and hand out",
            ),
        ),
        widget=forms.HiddenInput,
    )

    folder = forms.ChoiceField(
        label="Source folder",
        required=True,
    )

    name = forms.CharField(
        label="Assignment name",
        max_length=32,
        required=True,
    )

    description = forms.CharField(
        label="Description",
        max_length=500,
        required=True,
        widget=forms.Textarea(
            attrs={
                "rows": 3,
            }
        ),
    )

    valid_from = forms.DateTimeField(
        label="Valid from",
        required=False,
        input_formats=["%Y-%m-%dT%H:%M"],
        widget=forms.DateTimeInput(
            format="%Y-%m-%dT%H:%M",
            attrs={
                "type": "datetime-local",
            },
        ),
    )

    expires_at = forms.DateTimeField(
        label="Expires at",
        required=False,
        input_formats=["%Y-%m-%dT%H:%M"],
        widget=forms.DateTimeInput(
            format="%Y-%m-%dT%H:%M",
            attrs={
                "type": "datetime-local",
            },
        ),
    )

    remove_collected = forms.BooleanField(
        required=False,
        label=(
            "Remove the student's working copy "
            "when the assignment is collected"
        ),
    )

    def __init__(
        self,
        *args,
        available_folders,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        self.fields["folder"].choices = [
            (folder, folder)
            for folder in available_folders
        ]

    def clean(self):
        cleaned = super().clean()

        valid_from = cleaned.get("valid_from")
        expires_at = cleaned.get("expires_at")

        if (
            valid_from is not None
            and expires_at is not None
            and valid_from >= expires_at
        ):
            raise forms.ValidationError(
                "The validity start must be "
                "before the expiry time."
            )

        return cleaned


