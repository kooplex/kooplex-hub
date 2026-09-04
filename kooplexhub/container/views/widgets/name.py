import json

from django.template.response import TemplateResponse

from .base import ContainerEditorBaseView
from ...models import Container
from ...forms import ContainerNameForm
from ...services.editor_context import make_name_editor_context
from ...services.live import broadcast_container_runtime_changed


NAME_DISPLAY_TEMPLATE = "ui/editors/name/display.html"
NAME_EDIT_TEMPLATE = "ui/editors/name/edit.html"
CONTAINER_CREATE_NAME_FIELD_TEMPLATE = "container/partials/create/name_field.html"

class ContainerNameBaseView(ContainerEditorBaseView):
    field_name = "name"
    permission_name = "can_edit_name"
    editor_slug = "name"
    aria_label = "Change environment name"

    def get_form(self, *, data=None):
        container = self.get_container()

        return ContainerNameForm(
            data=data,
            instance=container,
            auto_id=f"container-{container.pk}-name-%s",
        )

    def make_editor_context(self, *, form=None):
        return make_name_editor_context(
            container=self.get_container(),
            presenter=self.get_presenter(),
            form=form,
        )


class ContainerNameDisplayView(ContainerNameBaseView):
    template_name = NAME_DISPLAY_TEMPLATE

    def get_context_data(self, **kwargs):
        return {
            "editor": self.make_editor_context(),
        }


class ContainerNameEditView(ContainerNameBaseView):
    template_name = NAME_EDIT_TEMPLATE

    def get_context_data(self, **kwargs):
        self.require_edit_permission()

        form = kwargs.get("form") or self.get_form()

        return {
            "editor": self.make_editor_context(
                form=form,
            ),
        }


class ContainerNameUpdateView(ContainerNameBaseView):
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        self.require_edit_permission()

        form = self.get_form(data=request.POST)

        if not form.is_valid():
            return TemplateResponse(
                request,
                NAME_EDIT_TEMPLATE,
                {
                    "editor": self.make_editor_context(
                        form=form,
                    ),
                },
            )

        container = form.save()

        self.refresh_editor_state(container)

        broadcast_container_runtime_changed(
            container,
            reason="container.name.updated",
        )

        response = TemplateResponse(
            request,
            NAME_DISPLAY_TEMPLATE,
            {
                "editor": self.make_editor_context(),
            },
        )

        response["HX-Trigger"] = json.dumps(
            {
                "kooplex-toast": {
                    "message": "Environment name updated.",
                    "level": "success",
                }
            }
        )

        return response


class ContainerCreateNameValidateView(ContainerNameBaseView):
    http_method_names = ["post"]

    def post(self, request):
        form = ContainerNameForm(
            data=request.POST,
            instance=Container(user=request.user),
            auto_id="container-create-name-%s",
        )

        form_is_valid = form.is_valid()

        response = TemplateResponse(
            request,
            CONTAINER_CREATE_NAME_FIELD_TEMPLATE,
            {
                "field": form["name"],
                "validated": form_is_valid,
            },
        )

        if form_is_valid:
            response["HX-Trigger-After-Swap"] = json.dumps(
                {
                    "container-create-name-valid": True,
                }
            )

        return response

