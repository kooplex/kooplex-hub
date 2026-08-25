from django.shortcuts import get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from ..models import UserCourseBinding
from ..services.course_presenter import CoursePresenter


class CourseAssignmentsView(
    LoginRequiredMixin, 
    TemplateView,
):
    template_name = "education/assignment/list.html"

    def get_binding(self):
        if not hasattr(self, "_binding"):
            self._binding = get_object_or_404(
                UserCourseBinding.objects.select_related("course"),
                user=self.request.user,
                course_id=self.kwargs["course_id"],
            )

        return self._binding

    def get_context_data(self, **kwargs):
        binding = self.get_binding()

        course_ui = CoursePresenter(
            binding=binding,
        )

        return {
            "course_ui": course_ui,
            "assignments": course_ui.get_assignments(),
        }


