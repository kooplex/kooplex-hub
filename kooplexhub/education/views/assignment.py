from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.views import View
from django.views.generic import TemplateView

from .mixins import CourseBindingMixin
from ..forms import (
    AssignmentScheduleForm,
)
from ..models import (
    UserCourseBinding,
    Assignment,
    UserAssignmentBinding,
)
from ..services.course_presenter import CoursePresenter
from ..services.assignments import (
    AssignmentActionError,
    handout_assignment_now,
    collect_assignment_now,
    submit_assignment,
    update_assignment_schedule,
)


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


class AssignmentActionBaseView(
    LoginRequiredMixin,
    CourseBindingMixin,
    View,
):
    template_name = "education/assignment/list.html"

    def get_assignment(self, *, manageable=False):
        queryset = Assignment.objects

        if manageable:
            queryset = queryset.manageable_by(
                self.request.user
            )
        else:
            queryset = queryset.visible_to(
                self.request.user
            )

        return get_object_or_404(
            queryset.select_related("course"),
            pk=self.kwargs["assignment_id"],
            course_id=self.kwargs["course_id"],
        )

    def render_assignment_list(
        self,
        *,
        status=200,
    ):
        # Deliberately construct a fresh presenter:
        # an action may have changed assignment state.
        course_ui = CoursePresenter(
            binding=self.get_binding(),
        )

        return TemplateResponse(
            self.request,
            self.template_name,
            {
                "course_ui": course_ui,
                "assignments": (
                    course_ui.get_assignments()
                ),
            },
            status=status,
        )


class AssignmentHandoutNowView(
    AssignmentActionBaseView
):
    def post(self, request, *args, **kwargs):
        assignment = self.get_assignment(
            manageable=True
        )

        try:
            handout_assignment_now(
                assignment=assignment,
                actor=request.user,
            )
        except AssignmentActionError as exc:
            return HttpResponseBadRequest(
                str(exc)
            )

        return self.render_assignment_list()


class AssignmentCollectNowView(
    AssignmentActionBaseView
):
    def post(self, request, *args, **kwargs):
        assignment = self.get_assignment(
            manageable=True
        )

        try:
            collect_assignment_now(
                assignment=assignment,
                actor=request.user,
            )
        except AssignmentActionError as exc:
            return HttpResponseBadRequest(
                str(exc)
            )

        return self.render_assignment_list()


class AssignmentSubmitView(
    AssignmentActionBaseView
):
    def post(self, request, *args, **kwargs):
        assignment = self.get_assignment()

        binding = get_object_or_404(
            UserAssignmentBinding.objects
            .select_related("assignment"),
            assignment=assignment,
            user=request.user,
        )

        try:
            submit_assignment(
                binding=binding,
                actor=request.user,
            )
        except AssignmentActionError as exc:
            return HttpResponseBadRequest(
                str(exc)
            )

        return self.render_assignment_list()


class AssignmentScheduleUpdateView(
    AssignmentActionBaseView
):
    def post(self, request, *args, **kwargs):
        assignment = self.get_assignment(
            manageable=True
        )

        form = AssignmentScheduleForm(
            request.POST
        )

        if not form.is_valid():
            return HttpResponseBadRequest(
                form.errors.as_text()
            )

        field = form.cleaned_data["field"]

        value = form.cleaned_data[field]

        try:
            update_assignment_schedule(
                assignment=assignment,
                actor=request.user,
                field=field,
                value=value,
            )
        except AssignmentActionError as exc:
            return HttpResponseBadRequest(
                str(exc)
            )

        return self.render_assignment_list()



