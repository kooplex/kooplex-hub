from django import forms
from django.contrib.auth import get_user_model

from container.models import Image
from volume.models import Volume

from ..models import Course
from ..services.members import (
    CourseMemberSelection,
    ROLE_STUDENT,
    ROLE_TEACHER,
)


User = get_user_model()


class CourseCreateForm(forms.ModelForm):

    creation_mode = forms.ChoiceField(
        choices=(
            ("course", "Create course"),
            (
                "course_and_environment",
                "Create course and environment",
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

    class Meta:
        model = Course
        fields = (
            "name",
            "description",
            "preferred_image",
        )

    def __init__(
        self,
        *args,
        actor,
        available_images,
        available_users,
        available_volumes,
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
            (),
        )

        members = []

        for user in selected_users:
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
        cleaned_data["mounts"] = tuple(
            cleaned_data.get("mounts", ())
        )

        return cleaned_data

    def get_selected_mounts(self):
        if not self.is_bound:
            selected_ids = self.initial.get(
                "mounts",
                (),
            )
        else:
            selected_ids = self.data.getlist(
                self.add_prefix("mounts")
            )

        if not selected_ids:
            return ()

        return tuple(
            self.fields["mounts"]
            .queryset
            .filter(pk__in=selected_ids)
        )

    def get_staged_member_selections(self):
        if not self.is_bound:
            return ()

        user_ids = self.data.getlist(
            self.add_prefix("member_users")
        )

        users = {
            str(user.pk): user
            for user in (
                self.fields["member_users"]
                .queryset
                .filter(pk__in=user_ids)
            )
        }

        selections = []

        for user_id in user_ids:
            user = users.get(str(user_id))

            if user is None:
                continue

            selections.append(
                CourseMemberSelection(
                    user=user,
                    role=self.data.get(
                        f"member_role_{user.pk}",
                        ROLE_STUDENT,
                    ),
                )
            )

        return tuple(selections)

