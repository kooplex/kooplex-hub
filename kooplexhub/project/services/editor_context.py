from django.urls import reverse

from ..conf import PROJECT_SETTINGS
from ..models import (
    Project,
    UserProjectBinding,
)
from .members import (
    MemberSelection,
    get_assignable_member_role_choices,
)


def get_project_scope_choices():
    icons = PROJECT_SETTINGS.presentation.scope_icons

    return tuple(
        {
            "value": value,
            "icon": icons[value],
            "label": value.replace("_", " ").title(),
            "description": description,
        }
        for value, description in Project.Scope.choices
    )


def get_project_scope_presentation(scope):
    choice = next(
        choice
        for choice in get_project_scope_choices()
        if choice["value"] == scope
    )
    return choice


def make_name_editor_context(
    *,
    project,
    presenter,
    form=None,
):
    return {
        "dom_id": f"project-{project.pk}-name",
        "value": project.name,
        "field": (
            form["name"] 
            if form is not None 
            else None
        ),
        "form": form,
        "can_edit": presenter.can_edit_name,
        "aria_label": "Change project name",
        "edit_url": reverse(
            "project:name-edit",
            kwargs={"project_id": project.pk},
        ),
        "display_url": reverse(
            "project:name-display",
            kwargs={"project_id": project.pk},
        ),
        "update_url": reverse(
            "project:name-update",
            kwargs={"project_id": project.pk},
        ),
    }


def make_description_editor_context(
    *,
    project,
    presenter,
    form=None,
):
    return {
        "dom_id": f"project-{project.pk}-description",
        "value": project.description,
        "field": (
            form["description"]
            if form is not None
            else None
        ),
        "form": form,
        "can_edit": presenter.can_edit_description,
        "aria_label": "Change project description",
        "edit_url": reverse(
            "project:description-edit",
            kwargs={"project_id": project.pk},
        ),
        "display_url": reverse(
            "project:description-display",
            kwargs={"project_id": project.pk},
        ),
        "update_url": reverse(
            "project:description-update",
            kwargs={"project_id": project.pk},
        ),
    }


def make_image_editor_context(
    *,
    project,
    presenter,
    form=None,
):
    return {
        "dom_id": f"project-{project.pk}-image",
        "selected_image": project.preferred_image,
        "field": (
            form["preferred_image"]
            if form is not None
            else None
        ),
        "form": form,
        "can_edit": presenter.can_change_image,
        "aria_label": "Change project's preferred image",
        "edit_url": reverse(
            "project:image-edit",
            kwargs={"project_id": project.pk},
        ),
        "display_url": reverse(
            "project:image-display",
            kwargs={"project_id": project.pk},
        ),
        "update_url": reverse(
            "project:image-update",
            kwargs={"project_id": project.pk},
        ),
    }


def make_create_image_editor_context(*, form):
    field = form["preferred_image"]

    return {
        "dom_id": "project-create-preferred-image",
        "field": field,
        "selected_value": str(field.value() or ""),
    }


def member_selection_to_context(selection):
    return {
        "user": selection.user,
        "role": selection.role,
    }


def member_binding_to_selection(binding):
    return MemberSelection(
        user=binding.user,
        role=binding.role,
    )

def get_form_member_selections(form):
    if (
        hasattr(form, "cleaned_data")
        and "members" in form.cleaned_data
    ):
        return tuple(
            form.cleaned_data["members"]
        )

    if hasattr(
        form,
        "get_staged_member_selections",
    ):
        return (
            form.get_staged_member_selections()
        )

    return ()


def make_project_member_presentation(
    *,
    binding,
):
    role_labels = {
        UserProjectBinding.Role.CREATOR: "Creator",
        UserProjectBinding.Role.ADMIN: "Administrator",
        UserProjectBinding.Role.COLLABORATOR: "Member",
    }
    role_icons = (
        PROJECT_SETTINGS
        .presentation
        .member_role_icons
    )

    return {
        "user": binding.user,
        "role": binding.role,
        "role_label": role_labels[
            binding.role
        ],
        "role_icon": role_icons.get(
            binding.role,
            "bi-person",
        ),
        "is_creator": (
            binding.role
            == UserProjectBinding.Role.CREATOR
        )
    }


def make_member_summary_context(
    *,
    project,
    presenter,
):
    role_labels = dict(
        UserProjectBinding.Role.assignable_choices()
    )

    bindings = (
        project.userbindings
        .select_related("user")
        .all()
    )

    actor = presenter.user
    members = []

    for binding in bindings:
        if binding.user_id ==actor.pk:
            continue

        members.append(
            make_project_member_presentation(
                binding=binding,
            )
        )

    return {
        "dom_id": f"project-{project.pk}-members",
        "members": tuple(members),
        "extra_member_count": max(
            len(members) - 3,
            0,
        ),
        "can_edit": presenter.can_manage_members,
        "modal_url": reverse(
            "project:members-modal",
            kwargs={
                "project_id": project.pk,
            },
        ),
        "display_url": reverse(
            "project:members-display",
            kwargs={
                "project_id": project.pk,
            },
        ),
    }


def make_member_editor_context(
    *,
    project,
    presenter,
):
    kwargs = {
        "project_id": project.pk,
    }

    selections = [
        member_binding_to_selection(binding)
        for binding in (
            project.userbindings
            .exclude(
                role=(
                    UserProjectBinding
                    .Role
                    .CREATOR
                )
            )
            .select_related("user")
        )
    ]

    return {
        "dom_id": f"project-{project.pk}-members",
        "selected_members": [
            member_selection_to_context(
                selection
            )
            for selection in selections
        ],
        "role_choices": (
            get_assignable_member_role_choices()
        ),
        "can_edit": presenter.can_manage_members,
        "staged": False,
        "display_url": reverse(
            "project:members-display",
            kwargs=kwargs,
        ),
        "edit_url": reverse(
            "project:members-edit",
            kwargs=kwargs,
        ),
        "update_url": reverse(
            "project:members-update",
            kwargs=kwargs,
        ),
        "search_url": reverse(
            "project:members-search",
            kwargs=kwargs,
        ),
    }

def make_create_member_editor_context(
    *,
    form,
):
    selections = get_form_member_selections(
        form
    )
    return {
        "dom_id": "project-create-members",
        "selected_members": [
            member_selection_to_context(
                selection
            )
            for selection in selections
        ],
        "role_choices": (
            get_assignable_member_role_choices()
        ),
        "can_edit": True,
        "staged": True,
        "search_url": reverse(
            "project:create-members-search",
        ),
    }


def make_membership_ui(*, dom_id):
    return {
        "dom_id": dom_id,
        "members_target": f"#{dom_id}-members",
        "search_results_target": (
            f"#{dom_id}-search-results"
        ),
        "role_choices": (
            get_assignable_member_role_choices()
        ),
    }


def make_mounts_summary_context(
    *,
    project,
    presenter,
):
    kwargs = {
        "project_id": project.pk,
    }

    selected_mounts = tuple(
        binding.volume
        for binding in (
            project.volumebindings
            .select_related("volume")
        )
    )

    return {
        "dom_id": f"project-{project.pk}-volumes",
        "selected_mounts": selected_mounts,
        "can_edit": presenter.can_change_mounts,
        "modal_url": reverse(
            "project:mounts-edit",
            kwargs=kwargs,
        ),
        "display_url": reverse(
            "project:mounts-display",
            kwargs=kwargs,
        ),
        "update_url": reverse(
            "project:mounts-update",
            kwargs=kwargs,
        ),
    }


def make_create_mounts_editor_context(
    *,
    form,
):
    selected_mounts = (
        form.get_selected_mounts()
    )

    selected_ids = {
        volume.pk
        for volume in selected_mounts
    }

    available_mounts = tuple(
        form.fields["mounts"].queryset
    )

    return {
        "dom_id": "project-create-mounts",
        "selected_mounts": selected_mounts,
        "available_mounts": available_mounts,
        "items": tuple(
            {
                "volume": volume,
                "selected": volume.pk in selected_ids,
            }
            for volume in available_mounts
        ),
        "field": form["mounts"],
        "form": form,
        "can_edit": True,
        "staged": True,
    }


def make_scope_editor_context(
    *,
    project,
    presenter,
    form=None,
):
    kwargs = {
        "project_id": project.pk,
    }

    presentation = get_project_scope_presentation(project.scope)

    return {
        "dom_id": f"project-{project.pk}-scope",
        "value": project.scope,
        "field": (
            form["scope"] 
            if form is not None 
            else None
        ),
        "form": form,
        "can_edit": presenter.can_change_scope,
        "aria_label": "Change project scope",
        "display_value": presentation["label"],
        "icon": presentation["icon"],
        "description": presentation["description"],
        "choices": get_project_scope_choices(),
        "edit_url": reverse(
            "project:scope-edit",
            kwargs=kwargs,
        ),
        "display_url": reverse(
            "project:scope-display",
            kwargs=kwargs,
        ),
        "update_url": reverse(
            "project:scope-update",
            kwargs=kwargs,
        ),
    }



