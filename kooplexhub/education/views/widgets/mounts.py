import json
import logging

from django.http import HttpResponse
from django.template.response import TemplateResponse

from .base import CourseEditorBaseView

from ...forms import CourseMountsForm
from ...models import VolumeCourseBinding
from ...services.mounts import update_course_mounts
from ...services.editor_context import COURSE_MOUNTS_UPDATED_EVENT


logger = logging.getLogger(__name__)


MOUNTS_DISPLAY_TEMPLATE = (
    "ui/editors/mounts_picker/summary.html"
)

MOUNTS_MODAL_TEMPLATE = (
    "ui/editors/mounts_picker/modal.html"
)

MOUNTS_MODAL_CONTENT_TEMPLATE = (
    "ui/editors/mounts_picker/modal_content.html"
)


class CourseMountsBaseView(
    CourseEditorBaseView
):
    field_name = None
    permission_name = "can_change_mounts"
    editor_slug = "mounts"
    aria_label = "Manage course mounts"
    refresh_event = COURSE_MOUNTS_UPDATED_EVENT

    def get_form(self, *, data=None):
        course = self.get_course()

        initial_mount_ids = (
            VolumeCourseBinding.objects
            .filter(course=course)
            .values_list(
                "volume_id",
                flat=True,
            )
        )

        return CourseMountsForm(
            data=data,
            actor=self.request.user,
            initial={
                "mounts": initial_mount_ids,
            },
            auto_id=(
                f"course-{course.pk}-mounts-%s"
            ),
        )

    def extend_editor_context(
        self,
        context,
        *,
        form=None,
    ):
        course = self.get_course()

        if form is None:
            selected_mounts = tuple(
                binding.volume
                for binding in (
                    VolumeCourseBinding.objects
                    .filter(course=course)
                    .select_related("volume")
                )
            )
            available_mounts = ()

        else:
            available_mounts = tuple(
                form.fields["mounts"].queryset
            )

            if form.is_bound:
                selected_mounts = (
                    form.get_selected_mounts()
                )
            else:
                selected_mounts = tuple(
                    binding.volume
                    for binding in (
                        VolumeCourseBinding.objects
                        .filter(course=course)
                        .select_related("volume")
                    )
                )

        selected_ids = {
            volume.pk
            for volume in selected_mounts
        }

        context.update({
            "selected_mounts": selected_mounts,
            "available_mounts": available_mounts,
            "items": tuple(
                {
                    "volume": volume,
                    "selected": (
                        volume.pk in selected_ids
                    ),
                }
                for volume in available_mounts
            ),
            "staged": False,
            "refresh_event": self.refresh_event,
        })

        return context


class CourseMountsDisplayView(
    CourseMountsBaseView
):
    template_name = MOUNTS_DISPLAY_TEMPLATE

    def get_context_data(self, **kwargs):
        return {
            "editor": self.make_editor_context(),
        }


class CourseMountsModalView(
    CourseMountsBaseView
):
    template_name = MOUNTS_MODAL_TEMPLATE

    def get_context_data(self, **kwargs):
        self.require_edit_permission()

        form = (
            kwargs.get("form")
            or self.get_form()
        )

        return {
            "editor": self.make_editor_context(
                form=form
            ),
        }


class CourseMountsUpdateView(
    CourseMountsBaseView
):
    http_method_names = ["post"]

    def post(
        self,
        request,
        *args,
        **kwargs,
    ):
        self.require_edit_permission()

        form = self.get_form(
            data=request.POST,
        )

        if not form.is_valid():
            return TemplateResponse(
                request,
                MOUNTS_MODAL_CONTENT_TEMPLATE,
                {
                    "editor": (
                        self.make_editor_context(
                            form=form
                        )
                    ),
                },
                status=422,
            )

        course = self.get_course()

        changes = update_course_mounts(
            course=course,
            mounts=form.cleaned_data["mounts"],
        )

        if changes.changed:
            logger.info(
                "Course %s mounts changed by %s: "
                "%d added, %d removed",
                course.pk,
                request.user.pk,
                len(changes.added),
                len(changes.removed),
            )

        response = HttpResponse(status=204)

        response["HX-Trigger"] = json.dumps({
            "modal-close": True,
            "course-mounts-updated": {
                "course_id": course.pk,
            },
        })

        return response


