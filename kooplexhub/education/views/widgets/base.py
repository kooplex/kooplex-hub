import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.urls import reverse
from django.views.generic import TemplateView

from ..mixins import CourseBindingMixin

logger = logging.getLogger(__name__)


class CourseEditorBaseView(
    LoginRequiredMixin,
    CourseBindingMixin,
    TemplateView,
):
    field_name = None
    permission_name = None
    editor_slug = None
    aria_label = None

    def require_edit_permission(self):
        presenter = self.get_presenter()

        if not getattr(presenter, self.permission_name):
            raise PermissionDenied

        return presenter

    def get_editor_urls(self):
        course = self.get_course()
        kwargs = {"course_id": course.pk}

        return {
            "edit_url": reverse(
                f"education:{self.editor_slug}-edit",
                kwargs=kwargs,
            ),
            "display_url": reverse(
                f"education:{self.editor_slug}-display",
                kwargs=kwargs,
            ),
            "update_url": reverse(
                f"education:{self.editor_slug}-update",
                kwargs=kwargs,
            ),
        }

    def get_editor_value(self):
        if self.field_name is None:
            return None

        return getattr(
            self.get_course(),
            self.field_name,
        )

    def get_editor_field(self, *, form=None):
        if form is None or self.field_name is None:
            return None

        return form[self.field_name]

    def extend_editor_context(
        self,
        context,
        *,
        form=None,
    ):
        return context

    def make_editor_context(self, *, form=None):
        course = self.get_course()
        presenter = self.get_presenter()

        context = {
            "dom_id": (
                f"course-{course.pk}-"
                f"{self.editor_slug}"
            ),
            "value": self.get_editor_value(),
            "field": self.get_editor_field(
                form=form,
            ),
            "form": form,
            "can_edit": getattr(
                self.get_presenter(),
                self.permission_name,
            ),
            "aria_label": self.aria_label,
            **self.get_editor_urls(),
        }

        return self.extend_editor_context(
            context,
            form=form,
        )

    def refresh_editor_state(self, course):
        self.course = course
        self.presenter = None

