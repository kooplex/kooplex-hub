from django import forms
from django.contrib.auth import get_user_model

from .mixins import MemberSelectionFormMixin

User = get_user_model()


class ProjectMembersForm(
    MemberSelectionFormMixin,
    forms.Form,
):
    member_users = forms.ModelMultipleChoiceField(
        queryset=User.objects.none(),
        required=False,
        widget=forms.MultipleHiddenInput,
    )

    def __init__(
        self, 
        *args, 
        actor, 
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        self.actor = actor

        submitted_ids = {
            int(value)
            for value in self.data.getlist("member_users")
            if value.isdigit()
        }

        self.fields["member_users"].queryset = (
            User.objects.filter(
                pk__in=submitted_ids,
                is_active=True,
            )
        )

    def clean(self):
        cleaned_data = super().clean()

        users = cleaned_data.get("member_users")

        if users is None:
            cleaned_data["members"] = ()
            return cleaned_data

        cleaned_data["members"] = (
            self.make_member_selections(
                users=users,
                excluded_user_ids={
                    self.actor.pk,
                },
                default_role=None,
            )
        )

        return cleaned_data


