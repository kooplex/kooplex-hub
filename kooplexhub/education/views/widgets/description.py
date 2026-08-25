import json

from django.template.response import TemplateResponse

from .base import CourseEditorBaseView
from ...models import Course
from ...forms import CourseDescriptionForm
from ...services.editor_context import make_description_editor_context


DESCRIPTION_DISPLAY_TEMPLATE = "ui/editors/description/display.html"
DESCRIPTION_EDIT_TEMPLATE = "ui/editors/description/edit.html"
COURSE_CREATE_DESCRIPTION_FIELD_TEMPLATE = "education/course/partials/create/description_field.html"


class CourseDescriptionBaseView(CourseEditorBaseView):
    field_name = "description"
    permission_name = "can_edit_description"
    editor_slug = "description"
    aria_label = "Change course description"

    def get_form(self, *, data=None):
        course = self.get_course()

        return CourseDescriptionForm(
            data=data,
            instance=course,
            auto_id=f"course-{course.pk}-description-%s",
        )

    def make_editor_context(self, *, form=None):
        return make_description_editor_context(
            course=self.get_course(),
            presenter=self.get_presenter(),
            form=form,
        )


class CourseDescriptionDisplayView(
    CourseDescriptionBaseView,
):
    template_name = DESCRIPTION_DISPLAY_TEMPLATE

    def get_context_data(self, **kwargs):
        return {
            "editor": self.make_editor_context(),
        }


class CourseDescriptionEditView(
    CourseDescriptionBaseView,
):
    template_name = DESCRIPTION_EDIT_TEMPLATE

    def get_context_data(self, **kwargs):
        self.require_edit_permission()

        form = kwargs.get("form") or self.get_form()

        return {
            "editor": self.make_editor_context(form=form),
        }


class CourseDescriptionUpdateView(
    CourseDescriptionBaseView,
):
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        self.require_edit_permission()

        form = self.get_form(data=request.POST)

        if not form.is_valid():
            return TemplateResponse(
                request,
                DESCRIPTION_EDIT_TEMPLATE,
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


class CourseCreateDescriptionValidateView(
    CourseDescriptionBaseView,
):
    http_method_names = ["post"]

    def post(self, request):
        form = CourseDescriptionForm(
            data=request.POST,
            instance=Course(),
            auto_id="course-create-description-%s",
        )

        form_is_valid = form.is_valid()

        response = TemplateResponse(
            request,
            COURSE_CREATE_DESCRIPTION_FIELD_TEMPLATE,
            {
                "field": form["description"],
            },
        )

        if form_is_valid:
            response["HX-Trigger-After-Swap"] = json.dumps(
                {
                    "course-create-description-valid": True,
                }
            )

        return response


