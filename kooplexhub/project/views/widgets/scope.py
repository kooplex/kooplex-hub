from django.template.response import TemplateResponse

from .base import ProjectEditorBaseView
from ...forms import ProjectScopeForm
from ...services.editor_context import (
    get_project_scope_presentation,
    get_project_scope_choices,
)

SCOPE_DISPLAY_TEMPLATE = "ui/editors/scope/display.html"
SCOPE_EDIT_TEMPLATE = "ui/editors/scope/edit.html"



class ProjectScopeBaseView(ProjectEditorBaseView):
    field_name = "scope"
    permission_name = "can_change_scope"
    editor_slug = "scope"
    aria_label = "Change project scope"

    def get_form(self, *, data=None):
        project = self.get_project()

        return ProjectScopeForm(
            data=data,
            instance=project,
            auto_id=f"project-{project.pk}-scope-%s",
        )

    def extend_editor_context(
        self,
        context,
        *,
        form=None,
    ):
        project = self.get_project()
        presentation = get_project_scope_presentation(project.scope)

        context.update({
            "icon": presentation["icon"],
            "display_value": presentation["label"],
            "description": presentation["description"],
            "choices": get_project_scope_choices(),
        })

        return context


class ProjectScopeDisplayView(ProjectScopeBaseView):
    template_name = SCOPE_DISPLAY_TEMPLATE

    def get_context_data(self, **kwargs):
        return {
            "editor": self.make_editor_context(),
        }


class ProjectScopeEditView(ProjectScopeBaseView):
    template_name = SCOPE_EDIT_TEMPLATE

    def get_context_data(self, **kwargs):
        self.require_edit_permission()
        form = kwargs.get("form") or self.get_form()

        return {
            "editor": self.make_editor_context(
                form=form,
            ),
        }


class ProjectScopeUpdateView(ProjectScopeBaseView):
    http_method_names = ["post"]
    template_name = SCOPE_EDIT_TEMPLATE

    def post(self, request, *args, **kwargs):
        self.require_edit_permission()

        form = self.get_form(data=request.POST)

        if not form.is_valid():
            return TemplateResponse(
                request,
                self.template_name,
                {
                    "editor": self.make_editor_context(
                        form=form,
                    ),
                },
            )

        project = form.save()
        self.refresh_editor_state(project)

        return TemplateResponse(
            request,
            SCOPE_DISPLAY_TEMPLATE,
            {
                "editor": self.make_editor_context(),
            },
        )


