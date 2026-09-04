from django.urls import reverse


def make_name_editor_context(
    *,
    container,
    presenter,
    form=None,
):
    return {
        "dom_id": f"container-{container.pk}-name",
        "value": container.name,
        "field": (
            form["name"]
            if form is not None
            else None
        ),
        "form": form,
        "can_edit": presenter.can_edit_name,
        "aria_label": "Change environment name",
        "edit_url": reverse(
            "container:name-edit",
            kwargs={"container_id": container.pk},
        ),
        "display_url": reverse(
            "container:name-display",
            kwargs={"container_id": container.pk},
        ),
        "update_url": reverse(
            "container:name-update",
            kwargs={"container_id": container.pk},
        ),
    }


