import logging
from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.db import transaction

from ..models import UserProjectBinding

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MemberSelection:
    user: object
    role: str

    @property
    def user_id(self):
        return self.user.pk


@dataclass(frozen=True)
class MembershipChanges:
    added: tuple
    updated: tuple
    removed: tuple

    @property
    def changed(self):
        return bool(
            self.added 
            or self.updated 
            or self.removed
        )


def get_assignable_member_roles():
    return {
        value
        for value, _label
        in UserProjectBinding.Role.assignable_choices()
    }

def get_assignable_member_role_choices():
    return [
        {
            "value": value,
            "label": label,
        }
        for value, label
        in UserProjectBinding.Role.assignable_choices()
    ]



def build_member_selections(
    *,
    users,
    roles_by_user_id,
    excluded_user_ids=(),
    default_role=None,
):
    """
    Convert users and submitted role values into validated
    MemberSelection objects.

    When default_role is None, every user must have an explicitly
    submitted role.
    """
    allowed_roles = get_assignable_member_roles()
    excluded_user_ids = set(excluded_user_ids)

    selections = []
    errors = []

    for user in users:
        if user.pk in excluded_user_ids:
            continue

        role = roles_by_user_id.get(user.pk, default_role)

        if not role:
            errors.append(
                f"No role was selected for {user.username}."
            )
            continue

        if role not in allowed_roles:
            errors.append(
                f"Invalid role submitted for {user.username}."
            )
            continue

        selections.append(
            MemberSelection(
                user=user,
                role=role,
            )
        )

    if errors:
        raise ValidationError({
            "members": errors,
        })

    return tuple(selections)


def validate_member_selections(
    *,
    selections,
    excluded_user_ids=(),
):
    return build_member_selections(
        users=[
            selection.user
            for selection in selections
        ],
        roles_by_user_id={
            selection.user_id: selection.role
            for selection in selections
        },
        excluded_user_ids=excluded_user_ids,
    )


@transaction.atomic
def create_project_members(
    *,
    project,
    owner,
    members,
):
    selections = validate_member_selections(
        selections=members,
        excluded_user_ids={owner.pk},
    )

    return apply_project_members(
        project=project,
        selections=selections,
    )


@transaction.atomic
def apply_project_members(
    *,
    project,
    selections,
):
    desired = {
        selection.user.pk: selection
        for selection in selections
    }

    editable_bindings = list(
        UserProjectBinding.objects
        .filter(project=project)
        .exclude(
            role=UserProjectBinding.Role.CREATOR
        )
        .select_related("user")
    )

    existing = {
        binding.user_id: binding
        for binding in editable_bindings
    }

    added = []
    updated = []
    removed = []

    for user_id, selection in desired.items():
        binding = existing.get(user_id)

        if binding is None:
            binding = UserProjectBinding.objects.create(
                project=project,
                user=selection.user,
                role=selection.role,
            )
            added.append(binding)
            continue

        if binding.role != selection.role:
            binding.role = selection.role
            binding.save(update_fields=["role"])
            updated.append(binding)

    for user_id, binding in existing.items():
        if user_id not in desired:
            removed.append(binding)
            binding.delete()

    return MembershipChanges(
        added=tuple(added),
        updated=tuple(updated),
        removed=tuple(removed),
    )


@transaction.atomic
def update_project_members(
    *,
    project,
    actor,   #NOTE: consider removing
    members,
):
    creator_user_ids = set(
        UserProjectBinding.objects
        .filter(
            project=project,
            role=UserProjectBinding.Role.CREATOR,
        )
        .values_list(
            "user_id", 
            flat=True
        )
    )

    selections = validate_member_selections(
        selections=members,
        excluded_user_ids=(
            creator_user_ids | {actor.pk}
        ),
    )

    return apply_project_members(
        project=project,
        selections=selections,
    )


