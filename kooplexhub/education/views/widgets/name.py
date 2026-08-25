import json

from django.template.response import TemplateResponse

from .base import CourseEditorBaseView
from ...models import Course
from ...forms import CourseNameForm
from ...services.editor_context import make_name_editor_context


NAME_DISPLAY_TEMPLATE = "ui/editors/name/display.html"
NAME_EDIT_TEMPLATE = "ui/editors/name/edit.html"
COURSE_CREATE_NAME_FIELD_TEMPLATE = "education/course/partials/create/name_field.html"


class CourseNameBaseView(CourseEditorBaseView):
    field_name = "name"
    permission_name = "can_edit_name"
    editor_slug = "name"
    aria_label = "Change course name"

    def get_form(self, *, data=None):
        course = self.get_course()

        return CourseNameForm(
            data=data,
            instance=course,
            auto_id=f"course-{course.pk}-name-%s",
        )

    def make_editor_context(self, *, form=None):
        return make_name_editor_context(
            course=self.get_course(),
            presenter=self.get_presenter(),
            form=form,
        )


class CourseNameDisplayView(CourseNameBaseView):
    template_name = NAME_DISPLAY_TEMPLATE

    def get_context_data(self, **kwargs):
        return {
            "editor": self.make_editor_context(),
        }


class CourseNameEditView(CourseNameBaseView):
    template_name = NAME_EDIT_TEMPLATE

    def get_context_data(self, **kwargs):
        self.require_edit_permission()

        form = kwargs.get("form") or self.get_form()

        return {
            "editor": self.make_editor_context(form=form),
        }


class CourseNameUpdateView(CourseNameBaseView):
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


class CourseCreateNameValidateView(CourseNameBaseView):
    http_method_names = ["post"]

    def post(self, request):
        form = CourseNameForm(
            data=request.POST,
            instance=Course(),
            auto_id="course-create-name-%s",
        )

        form_is_valid = form.is_valid()

        response = TemplateResponse(
            request,
            COURSE_CREATE_NAME_FIELD_TEMPLATE,
            {
                "field": form["name"],
                "validated": form_is_valid,
            },
        )

        if form_is_valid:
            response["HX-Trigger-After-Swap"] = json.dumps(
                {
                    "course-create-name-valid": True,
                }
            )

        return response


