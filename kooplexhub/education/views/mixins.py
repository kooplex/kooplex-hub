from django.shortcuts import get_object_or_404

from ..models import (
    Course,
    UserCourseBinding,
)
from ..services.course_presenter import CoursePresenter


class CourseBindingMixin:
    _course_binding = None
    _course_presenter = None

    def get_course_binding_queryset(self):
        return (
            UserCourseBinding.objects
            .for_user(self.request.user)
            .with_course()
        )

    def get_binding(self):
        if self._course_binding is None:
            self._course_binding = get_object_or_404(
                self.get_course_binding_queryset(),
                course_id=self.kwargs["course_id"],
            )

        return self._course_binding

    def get_course(self):
        return self.get_binding().course

    def get_presenter(self):
        if self._course_presenter is None:
            self._course_presenter = CoursePresenter(
                binding=self.get_binding(),
            )

        return self._course_presenter



class CourseListQuerysetMixin(CourseBindingMixin):
    context_object_name = "coursebindings"

    def get_queryset(self):
        return (
            self.get_course_binding_queryset()
            .ordered_for_dashboard()
        )
