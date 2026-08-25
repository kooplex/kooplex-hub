from django.urls import reverse

from .members import (
    ROLE_STUDENT,
    ROLE_TEACHER,
    get_assignable_member_role_choices,
)
from ..models import VolumeCourseBinding

COURSE_MOUNTS_UPDATED_EVENT = "course-mounts-updated"
COURSE_MEMBERS_UPDATED_EVENT = "course-members-updated"


def make_course_member_presentation(*, binding):
    role = binding.role

    return {
        "user": binding.user,
        "role": role,
        "role_label": (
            "Teacher"
            if role == ROLE_TEACHER
            else "Student"
        ),
        "role_icon": (
            "bi-person-workspace"
            if role == ROLE_TEACHER
            else "bi-mortarboard"
        ),
    }


def make_member_editor_urls(course):
    kwargs = {
        "course_id": course.pk,
    }

    return {
        "display_url": reverse(
            "education:members-display",
            kwargs=kwargs,
        ),
        "modal_url": reverse(
            "education:members-modal",
            kwargs=kwargs,
        ),
        "update_url": reverse(
            "education:members-update",
            kwargs=kwargs,
        ),
        "search_url": reverse(
            "education:members-search",
            kwargs=kwargs,
        ),
    }


def member_selection_to_context(selection):
    return {
        "user": selection.user,
        "role": selection.role,
        "role_label": (
            "Teacher"
            if selection.role == ROLE_TEACHER
            else "Student"
        ),
        "role_icon": (
            "bi-person-workspace"
            if selection.role == ROLE_TEACHER
            else "bi-mortarboard"
        ),
    }


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
            "education:name-edit",
            kwargs={"course_id": course.pk},
        ),
        "display_url": reverse(
            "education:name-display",
            kwargs={"course_id": course.pk},
        ),
        "update_url": reverse(
            "education:name-update",
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
            "education:description-edit",
            kwargs={"course_id": course.pk},
        ),
        "display_url": reverse(
            "education:description-display",
            kwargs={"course_id": course.pk},
        ),
        "update_url": reverse(
            "education:description-update",
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
    bindings = (
        course.userbindings
        .select_related("user")
        .order_by(
            "-is_teacher",
            "user__last_name",
            "user__first_name",
            "user__username",
        )
    )

    members = tuple(
        make_course_member_presentation(
            binding=binding,
        )
        for binding in bindings
    )

    kwargs = {
        "course_id": course.pk,
    }

    return {
        "dom_id": f"course-{course.pk}-members",
        "members": members,
        "can_edit": presenter.can_manage_members,
        "title": "Manage course members",
        "refresh_event": COURSE_MEMBERS_UPDATED_EVENT,
        **make_member_editor_urls(course),
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


def make_image_editor_context(
    *,
    course,
    presenter,
):
    kwargs = {
        "course_id": course.pk,
    }

    return {
        "dom_id": f"course-{course.pk}-image",
        "selected_image": course.preferred_image,
        "field": None,
        "form": None,
        "can_edit": presenter.can_change_image,
        "aria_label": "Change course's preferred image",
        "edit_url": reverse(
            "education:image-edit",
            kwargs=kwargs,
        ),
        "display_url": reverse(
            "education:image-display",
            kwargs=kwargs,
        ),
        "update_url": reverse(
            "education:image-update",
            kwargs=kwargs,
        ),
    }


def make_mounts_summary_context(
    *,
    course,
    presenter,
):
    kwargs = {
        "course_id": course.pk,
    }

    selected_mounts = tuple(
        binding.volume
        for binding in (
            VolumeCourseBinding.objects
            .filter(course=course)
            .select_related("volume")
        )
    )

    return {
        "dom_id": f"course-{course.pk}-volumes",
        "selected_mounts": selected_mounts,
        "can_edit": presenter.can_change_mounts,
        "refresh_event": COURSE_MOUNTS_UPDATED_EVENT,
        "modal_url": reverse(
            "education:mounts-edit",
            kwargs=kwargs,
        ),
        "display_url": reverse(
            "education:mounts-display",
            kwargs=kwargs,
        ),
        "update_url": reverse(
            "education:mounts-update",
            kwargs=kwargs,
        ),
    }

