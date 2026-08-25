import json

from django.http import HttpResponse
from django.template.response import TemplateResponse

from container.services.image_catalog import ImageCatalogService

from .base import CourseEditorBaseView
from ...models import Course
from ...forms import CoursePreferredImageForm


IMAGE_DISPLAY_TEMPLATE = "ui/editors/image_picker/display.html"
IMAGE_MODAL_TEMPLATE = "ui/editors/image_picker/modal.html"
IMAGE_EDIT_TEMPLATE = "ui/editors/image_picker/edit.html"
COURSE_CREATE_PREFERRED_IMAGE_FIELD_TEMPLATE = "education/course/partials/create/preferred_image_field.html"


class CoursePreferredImageBaseView(CourseEditorBaseView):
    field_name = "preferred_image"
    permission_name = "can_change_image"
    editor_slug = "image"
    aria_label = "Change course's preferred image"

    def get_available_images(self):
        return ImageCatalogService.available_for_user(
            user=self.request.user,
        )

    def get_form(self, *, data=None):
        course = self.get_course()

        return CoursePreferredImageForm(
            data=data,
            instance=course,
            available_images=self.get_available_images(),
            auto_id=(
                f"course-{course.pk}"
                "-preferred-image-%s"
            ),
        )

    def make_editor_context(self, *, form=None):
        context = super().make_editor_context(form=form)

        context.update({
            "selected_image": self.get_course().preferred_image,
            "available_images": self.get_available_images(),
        })

        return context

class CoursePreferredImageDisplayView(
    CoursePreferredImageBaseView
):
    template_name = IMAGE_DISPLAY_TEMPLATE

    def get_context_data(self, **kwargs):
        return {
            "editor": self.make_editor_context(),
        }


class CoursePreferredImageChangeView(
    CoursePreferredImageBaseView
):
    template_name = IMAGE_MODAL_TEMPLATE

    def get_context_data(self, **kwargs):
        self.require_edit_permission()
        form = kwargs.get("form") or self.get_form()

        return {
            "editor": self.make_editor_context(form=form),
        }


class CoursePreferredImageUpdateView(
    CoursePreferredImageBaseView
):
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        self.require_edit_permission()
        form = self.get_form(data=request.POST)

        if not form.is_valid():
            return TemplateResponse(
                request,
                IMAGE_EDIT_TEMPLATE,
                {
                    "editor": self.make_editor_context(
                        form=form,
                    ),
                },
                status=422,
            )

        course = form.save()
        self.refresh_editor_state(course)
        editor = self.make_editor_context()

        response = TemplateResponse(
            request,
            IMAGE_DISPLAY_TEMPLATE,
            {
                "editor": editor,
            },
        )

        response["HX-Retarget"] = f"#{editor['dom_id']}"
        response["HX-Reswap"] = "outerHTML"
        response["HX-Trigger"] = json.dumps(
            {
                "closeModal": {
                    "modalId": f"{editor['dom_id']}-modal",
                }
            }
        )

        return response


class CourseCreatePreferredImageValidateView(
    CoursePreferredImageBaseView
):
    http_method_names = ["post"]

    def post(self, request):
        form = CoursePreferredImageForm(
            data=request.POST,
            instance=Course(),
            available_images=self.get_available_images(),
            auto_id=(
                f"course-create"
                "-preferred-image-%s"
            ),
        )

        is_valid = form.is_valid()

        response = TemplateResponse(
            request,
            COURSE_CREATE_PREFERRED_IMAGE_FIELD_TEMPLATE,
            {
                "field": form["preferred_image"],
            },
        )

        if is_valid:
            response[
                "HX-Trigger-After-Swap"
            ] = json.dumps({
                "course-create-image-valid": True,
            })

        return response
