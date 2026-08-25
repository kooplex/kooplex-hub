from django.shortcuts import get_object_or_404

from ..models import Course
from ..services.course_presenter import CoursePresenter



class CourseMemberAccessMixin:
    def get_course(self):
        return get_object_or_404(
            Course.objects
            .bound_to(self.request.user)
            .prefetch_related("userbindings__user"),
            pk=self.kwargs["pk"],
        )

    def get_presentation(self, course):
        return CoursePresenter(
            course=project,
            user=self.request.user,
        )

