from django.urls import reverse

from .members import (
    get_assignable_member_role_choices,
)


def make_name_editor_context(
    *,
    course,
    presenter,
    form=None,
):
    return {
        "dom_id": f"course-{course.pk}-name",
        "value": course.name,
        "field": (
            form["name"] 
            if form is not None 
            else None
        ),
        "form": form,
        "can_edit": presenter.can_edit_name,
        "aria_label": "Change course name",
        "edit_url": reverse(
            "course:name-edit",
            kwargs={"course_id": course.pk},
        ),
        "display_url": reverse(
            "course:name-display",
            kwargs={"course_id": course.pk},
        ),
        "update_url": reverse(
            "course:name-update",
            kwargs={"course_id": course.pk},
        ),
    }


def make_description_editor_context(
    *,
    course,
    presenter,
    form=None,
):
    return {
        "dom_id": f"course-{course.pk}-description",
        "value": course.description,
        "field": (
            form["description"]
            if form is not None
            else None
        ),
        "form": form,
        "can_edit": presenter.can_edit_description,
        "aria_label": "Change course description",
        "edit_url": reverse(
            "course:description-edit",
            kwargs={"course_id": course.pk},
        ),
        "display_url": reverse(
            "course:description-display",
            kwargs={"course_id": course.pk},
        ),
        "update_url": reverse(
            "course:description-update",
            kwargs={"course_id": course.pk},
        ),
    }


def make_create_image_editor_context(*, form):
    field = form["preferred_image"]

    return {
        "dom_id": "course-create-preferred-image",
        "field": field,
        "selected_value": str(field.value() or ""),
    }


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


def make_member_summary_context(
    *,
    course,
    presenter,
):
    role_labels = dict(
        UserCourseBinding.Role.assignable_choices()
    )

    bindings = (
        course.userbindings
        .select_related("user")
        .all()
    )

    actor = presenter.user
    members = []

    for binding in bindings:
        if binding.user_id ==actor.pk:
            continue

        members.append(
            make_course_member_presentation(
                binding=binding,
            )
        )

    return {
        "dom_id": f"course-{course.pk}-members",
        "members": tuple(members),
        "extra_member_count": max(
            len(members) - 3,
            0,
        ),
        "can_edit": presenter.can_manage_members,
        "modal_url": reverse(
            "course:members-modal",
            kwargs={
                "course_id": course.pk,
            },
        ),
        "display_url": reverse(
            "course:members-display",
            kwargs={
                "course_id": course.pk,
            },
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
        "dom_id": "course-create-members",
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
            "education:create-members-search",
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
        "dom_id": "course-create-mounts",
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



