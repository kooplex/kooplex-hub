import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import render
from django.views import View
from django.views.generic import TemplateView

from .mixins import CourseBindingMixin
from ..forms.assignment import AssignmentCreateForm
from ..services.assignments import (
    AssignmentActionError,
    create_assignment,
)
from ..filesystem import (
    get_assignment_prepare_subfolders,
)


ASSIGNMENT_CREATE_MODAL_TEMPLATE = (
    "education/assignment/create/modal.html"
)


class AssignmentCreateContextMixin(
    CourseBindingMixin
):
    def require_teacher(self):
        if not self.get_presenter().is_teacher:
            raise PermissionDenied

    def get_available_folders(self):
        return get_assignment_prepare_subfolders(
            self.get_course()
        )

    def get_form(self, *, data=None):
        return AssignmentCreateForm(
            data=data,
            available_folders=(
                self.get_available_folders()
            ),
            auto_id="assignment-create-%s",
        )

    def get_create_context(self, *, form):
        return {
            "course": self.get_course(),
            "course_ui": self.get_presenter(),
            "form": form,
        }


class AssignmentCreateModalView(
    LoginRequiredMixin,
    AssignmentCreateContextMixin,
    TemplateView,
):
    template_name = (
        ASSIGNMENT_CREATE_MODAL_TEMPLATE
    )

    def get(self, request, *args, **kwargs):
        self.require_teacher()
        return super().get(
            request,
            *args,
            **kwargs,
        )

    def get_context_data(self, **kwargs):
        return self.get_create_context(
            form=kwargs.get("form")
            or self.get_form()
        )


class AssignmentCreateView(
    LoginRequiredMixin,
    AssignmentCreateContextMixin,
    View,
):
    template_name = (
        ASSIGNMENT_CREATE_MODAL_TEMPLATE
    )

    def post(self, request, *args, **kwargs):
        self.require_teacher()

        form = self.get_form(
            data=request.POST,
        )

        if not form.is_valid():
            return render(
                request,
                self.template_name,
                self.get_create_context(
                    form=form,
                ),
                status=422,
            )

        try:
            assignment = create_assignment(
                course=self.get_course(),
                actor=request.user,
                folder=form.cleaned_data["folder"],
                name=form.cleaned_data["name"],
                description=(
                    form.cleaned_data[
                        "description"
                    ]
                ),
                valid_from=(
                    form.cleaned_data[
                        "valid_from"
                    ]
                ),
                expires_at=(
                    form.cleaned_data[
                        "expires_at"
                    ]
                ),
                remove_collected=(
                    form.cleaned_data[
                        "remove_collected"
                    ]
                ),
                handout_when_ready=(
                    form.cleaned_data[
                        "creation_mode"
                    ]
                    ==
                    AssignmentCreateForm
                    .MODE_CREATE_AND_HANDOUT
                ),
            )

        except AssignmentActionError as error:
            form.add_error(None, str(error))

            return render(
                request,
                self.template_name,
                self.get_create_context(
                    form=form,
                ),
                status=422,
            )

        response = HttpResponse(status=204)

        response["HX-Trigger"] = json.dumps({
            "modal-close": True,
            "course-assignments-updated": {
                "courseId": self.get_course().pk,
                "assignmentId": assignment.pk,
            },
        })

        return response



