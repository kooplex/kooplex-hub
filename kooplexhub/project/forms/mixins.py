from django import forms
from django.core.exceptions import ValidationError

from ..models import UserProjectBinding
from ..services.members import (
    build_member_selections,
)


class MemberSelectionFormMixin:
    member_users_field_name = "member_users"

    def get_submitted_member_ids(self):
        if not self.is_bound:
            return []

        return self.data.getlist(
            self.add_prefix(
                self.member_users_field_name
            )
        )

    def get_submitted_member_roles(self):
        roles = {}

        for submitted_id in (
            self.get_submitted_member_ids()
        ):
            try:
                user_id = int(submitted_id)
            except (TypeError, ValueError):
                continue

            roles[user_id] = self.data.get(
                self.add_prefix(
                    f"member_role_{user_id}"
                )
            )

        return roles

    def get_staged_member_selections(
        self,
        *,
        default_role=(
            UserProjectBinding
            .Role
            .COLLABORATOR
        ),
    ):
        if not self.is_bound:
            return ()

        submitted_ids = (
            self.get_submitted_member_ids()
        )

        users_by_id = {
            str(user.pk): user
            for user in self.fields[
                self.member_users_field_name
            ].queryset.filter(
                pk__in=submitted_ids,
            )
        }

        submitted_roles = (
            self.get_submitted_member_roles()
        )

        selections = []

        for submitted_id in submitted_ids:
            user = users_by_id.get(
                str(submitted_id)
            )

            if user is None:
                continue

            role = submitted_roles.get(
                user.pk
            ) or default_role

            selections.append(
                MemberSelection(
                    user=user,
                    role=role,
                )
            )

        return tuple(selections)

    def make_member_selections(
        self,
        *,
        users,
        excluded_user_ids=(),
        default_role=None,
    ):
        try:
            return build_member_selections(
                users=users,
                roles_by_user_id=(
                    self.get_submitted_member_roles()
                ),
                excluded_user_ids=excluded_user_ids,
                default_role=default_role,
            )
        except ValidationError as error:
            if hasattr(error, "message_dict"):
                messages = error.message_dict.get(
                    "members",
                    error.messages,
                )
            else:
                messages = error.messages

            for message in messages:
                self.add_error(None, message)

            return ()


