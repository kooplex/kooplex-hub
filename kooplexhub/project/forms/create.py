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
from volume.models import Volume

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

    mounts = forms.ModelMultipleChoiceField(
        queryset=Volume.objects.none(),
        required=False,
        widget=forms.MultipleHiddenInput,
    )

    def __init__(
        self,
        *args,
        available_images,
        available_users,
        available_volumes,
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

        self.fields["mounts"].queryset = (
            available_volumes
        )

    def clean(self):
        cleaned_data = super().clean()

        selected_users = cleaned_data.get(
            "member_users",
            ()
        )

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

        selected_mounts = cleaned_data.get(
            "mounts",
            (),
        )
    
        cleaned_data["mounts"] = tuple(
            selected_mounts
        )

        return cleaned_data

    def clean_name(self):
        return validate_project_name_for_creator(
            creator=self.actor,
            name=self.cleaned_data["name"],
        )

    def get_selected_mounts(self):
        if not self.is_bound:
            initial_values = self.initial.get(
                "mounts",
                (),
            )

            if not initial_values:
                return ()

            return tuple(
                self.fields["mounts"]
                .queryset
                .filter(pk__in=initial_values)
            )

        selected_ids = self.data.getlist(
            self.add_prefix("mounts")
        )

        if not selected_ids:
            return ()

        volumes_by_id = {
            str(volume.pk): volume
            for volume in (
                self.fields["mounts"]
                .queryset
                .filter(pk__in=selected_ids)
            )
        }

        return tuple(
            volumes_by_id[selected_id]
            for selected_id in selected_ids
            if selected_id in volumes_by_id
        )

