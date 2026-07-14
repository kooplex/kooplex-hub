import json

from ...forms.widgets import ContainerNameForm
from ...services.live import broadcast_container_live_event
from .base import (
    ContainerWidgetDisplayView,
    ContainerWidgetEditView,
    ContainerWidgetUpdateView,
)


class ContainerNameWidgetMixin:
    form_class = ContainerNameForm

    display_template_name = "ui/widgets/editable_text/display.html"
    edit_template_name = "ui/widgets/editable_text/form.html"

    def get_display_context(self, container):
        context = super().get_display_context(container)

        context.update(
            {
                "dom_id": container.name_dom_id,
                "value": container.name,
                "edit_url": container.name_edit_url,
            }
        )

        return context

    def get_edit_context(self, container, form):
        context = super().get_edit_context(container, form)

        context.update(
            {
                "dom_id": container.name_dom_id,
                "field_name": "name",
                "value": form["name"].value(),
                "update_url": container.name_update_url,
                "cancel_url": container.name_display_url,
                "field_errors": form["name"].errors,
            }
        )

        return context


class ContainerNameDisplayView(
    ContainerNameWidgetMixin,
    ContainerWidgetDisplayView,
):
    pass


class ContainerNameEditView(
    ContainerNameWidgetMixin,
    ContainerWidgetEditView,
):
    pass


class ContainerNameUpdateView(
    ContainerNameWidgetMixin,
    ContainerWidgetUpdateView,
):
    def after_save(self, container, form):
        broadcast_container_live_event(
            user=self.request.user,
            keys=[
                f"container:{container.pk}",
            ],
            payload={
                "event": "container.config.changed",
                "model": "container",
                "id": container.pk,
                "changed": ["name"],
            },
        )

    def add_success_headers(
        self,
        response,
        container,
        form,
    ):
        response["HX-Trigger"] = json.dumps(
            {
                "kooplex-toast": {
                    "message": "Environment name updated.",
                    "level": "success",
                }
            }
        )

        return response
