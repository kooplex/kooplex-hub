import json

from django.template.response import TemplateResponse

from .base import ProjectEditorBaseView
from ...models import Project
from ...forms import ProjectDescriptionForm
from ...services.editor_context import make_description_editor_context
from ...services.project import get_project_creator


DESCRIPTION_DISPLAY_TEMPLATE = "ui/editors/description/display.html"
DESCRIPTION_EDIT_TEMPLATE = "ui/editors/description/edit.html"
PROJECT_CREATE_DESCRIPTION_FIELD_TEMPLATE = "project/partials/create/description_field.html"


class ProjectDescriptionBaseView(ProjectEditorBaseView):
    field_name = "description"
    permission_name = "can_edit_description"
    editor_slug = "description"
    aria_label = "Change project description"

    def get_form(self, *, data=None):
        project = self.get_project()

        return ProjectDescriptionForm(
            data=data,
            instance=project,
            auto_id=f"project-{project.pk}-description-%s",
        )

    def make_editor_context(self, *, form=None):
        return make_description_editor_context(
            project=self.get_project(),
            presenter=self.get_presenter(),
            form=form,
        )


class ProjectDescriptionDisplayView(
    ProjectDescriptionBaseView,
):
    template_name = DESCRIPTION_DISPLAY_TEMPLATE

    def get_context_data(self, **kwargs):
        return {
            "editor": self.make_editor_context(),
        }


class ProjectDescriptionEditView(
    ProjectDescriptionBaseView,
):
    template_name = DESCRIPTION_EDIT_TEMPLATE

    def get_context_data(self, **kwargs):
        self.require_edit_permission()

        form = kwargs.get("form") or self.get_form()

        return {
            "editor": self.make_editor_context(form=form),
        }


class ProjectDescriptionUpdateView(
    ProjectDescriptionBaseView,
):
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        self.require_edit_permission()

        form = self.get_form(data=request.POST)

        if not form.is_valid():
            return TemplateResponse(
                request,
                DESCRIPTION_DISPLAY_TEMPLATE,
                {
                    "editor": self.make_editor_context(form=form),
                },
            )

        form.save()

        return TemplateResponse(
            request,
            DESCRIPTION_DISPLAY_TEMPLATE,
            {
                "editor": self.make_editor_context(),
            },
        )


class ProjectCreateDescriptionValidateView(
    ProjectDescriptionBaseView,
):
    http_method_names = ["post"]

    def post(self, request):
        form = ProjectDescriptionForm(
            data=request.POST,
            instance=Project(),
            auto_id="project-create-description-%s",
        )

        form_is_valid = form.is_valid()

        response = TemplateResponse(
            request,
            PROJECT_CREATE_DESCRIPTION_FIELD_TEMPLATE,
            {
                "field": form["description"],
            },
        )

        if form_is_valid:
            response["HX-Trigger-After-Swap"] = json.dumps(
                {
                    "project-create-description-valid": True,
                }
            )

        return response


