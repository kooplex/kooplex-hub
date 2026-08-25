from django import forms
from django.contrib.auth import get_user_model

from ..services.members import (
    CourseMemberSelection,
    ROLE_STUDENT,
    ROLE_TEACHER,
)


User = get_user_model()


class CourseMembersForm(forms.Form):
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
        self.fields["member_users"].queryset = (
            User.objects
            .filter(is_active=True)
            .exclude(pk=actor.pk)
        )

    def clean(self):
        cleaned_data = super().clean()

        users = cleaned_data.get(
            "member_users",
            (),
        )

        members = []

        for user in users:
            role = self.data.get(
                f"member_role_{user.pk}",
                ROLE_STUDENT,
            )

            if role not in {
                ROLE_STUDENT,
                ROLE_TEACHER,
            }:
                self.add_error(
                    "member_users",
                    f"Invalid role for {user}.",
                )
                continue

            members.append(
                CourseMemberSelection(
                    user=user,
                    role=role,
                )
            )

        cleaned_data["members"] = tuple(members)

        return cleaned_data

