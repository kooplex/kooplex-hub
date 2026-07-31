import logging
from django import forms
from django.contrib.auth import get_user_model

from ..models import (
    Project,
    UserProjectBinding,
)
from ..services.names import (
    validate_project_name_for_creator,
)
from .mixins import MemberSelectionFormMixin

logger = logging.getLogger(__name__)
User = get_user_model()


class ProjectCreateForm(
    MemberSelectionFormMixin,
    forms.ModelForm,
):
    class Meta:
        model = Project
        fields = [
            "name",
            "scope",
            "description",
            "preferred_image",
        ]

    creation_mode = forms.ChoiceField(
        choices=(
            ("project", "Create project"),
            (
                "project_and_environment",
                "Create project and environment",
            ),
        ),
        widget=forms.HiddenInput,
        required=False,
    )

    member_users = forms.ModelMultipleChoiceField(
        queryset=User.objects.none(),
        required=False,
        widget=forms.MultipleHiddenInput,
    )

    def __init__(
        self,
        *args,
        available_images,
        available_users,
        actor,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        self.actor = actor

        self.fields["preferred_image"].queryset = (
            available_images
        )
        self.fields["preferred_image"].required = True

        self.fields["member_users"].queryset = (
            available_users.exclude(pk=actor.pk)
        )

    def clean(self):
        cleaned_data = super().clean()

        selected_users = cleaned_data.get("member_users")

        if selected_users is None:
            cleaned_data["members"] = ()
            return cleaned_data
    
        cleaned_data["members"] = (
            self.make_member_selections(
                users=selected_users,
                excluded_user_ids={
                    self.actor.pk,
                },
                default_role=(
                    UserProjectBinding
                    .Role
                    .COLLABORATOR
                ),
            )
        )

        return cleaned_data

    def clean_name(self):
        return validate_project_name_for_creator(
            creator=self.actor,
            name=self.cleaned_data["name"],
        )


