import json

from django.template.response import TemplateResponse

from .base import ProjectEditorBaseView
from ...models import Project
from ...forms import ProjectNameForm
from ...services.editor_context import make_name_editor_context
from ...services.project import get_project_creator


NAME_DISPLAY_TEMPLATE = "ui/editors/name/display.html"
NAME_EDIT_TEMPLATE = "ui/editors/name/edit.html"
PROJECT_CREATE_NAME_FIELD_TEMPLATE = "project/partials/create/name_field.html"


class ProjectNameBaseView(ProjectEditorBaseView):
    field_name = "name"
    permission_name = "can_edit_name"
    editor_slug = "name"
    aria_label = "Change project name"

    def get_form(self, *, data=None):
        project = self.get_project()

        return ProjectNameForm(
            data=data,
            instance=project,
            creator=get_project_creator(project),
            auto_id=f"project-{project.pk}-name-%s",
        )

    def make_editor_context(self, *, form=None):
        return make_name_editor_context(
            project=self.get_project(),
            presenter=self.get_presenter(),
            form=form,
        )


class ProjectNameDisplayView(ProjectNameBaseView):
    template_name = NAME_DISPLAY_TEMPLATE

    def get_context_data(self, **kwargs):
        return {
            "editor": self.make_editor_context(),
        }


class ProjectNameEditView(ProjectNameBaseView):
    template_name = NAME_EDIT_TEMPLATE

    def get_context_data(self, **kwargs):
        self.require_edit_permission()

        form = kwargs.get("form") or self.get_form()

        return {
            "editor": self.make_editor_context(form=form),
        }


class ProjectNameUpdateView(ProjectNameBaseView):
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        self.require_edit_permission()

        form = self.get_form(data=request.POST)

        if not form.is_valid():
            return TemplateResponse(
                request,
                NAME_EDIT_TEMPLATE,
                {
                    "editor": self.make_editor_context(form=form),
                },
            )

        form.save()

        return TemplateResponse(
            request,
            NAME_DISPLAY_TEMPLATE,
            {
                "editor": self.make_editor_context(),
            },
        )


class ProjectCreateNameValidateView(ProjectNameBaseView):
    http_method_names = ["post"]

    def post(self, request):
        form = ProjectNameForm(
            data=request.POST,
            instance=Project(),
            creator=request.user,
            auto_id="project-create-name-%s",
        )

        form_is_valid = form.is_valid()

        response = TemplateResponse(
            request,
            PROJECT_CREATE_NAME_FIELD_TEMPLATE,
            {
                "field": form["name"],
                "validated": form_is_valid,
            },
        )

        if form_is_valid:
            response["HX-Trigger-After-Swap"] = json.dumps(
                {
                    "project-create-name-valid": True,
                }
            )

        return response


