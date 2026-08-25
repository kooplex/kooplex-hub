import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseForbidden
from django.shortcuts import render
from django.views import View

from ..mixins import CourseBindingMixin

from ...services.environments import (
    CourseEnvironmentCreationError,
    create_default_course_environment,
)


class CourseEnvironmentTabMixin:
    template_name = (
        "education/course/partials/tabs/environment.html"
    )

    def render_tab(
        self,
        course,
        presentation,
        **extra,
    ):
        return render(
            self.request,
            self.template_name,
            {
                "course": course,
                "presentation": presentation,
                **extra,
            },
        )


class CourseEnvironmentTabView(
    LoginRequiredMixin,
    CourseBindingMixin,
    CourseEnvironmentTabMixin,
    View,
):
    def get(self, request, *args, **kwargs):
        return self.render_tab(
            self.get_course(),
            self.get_presenter(),
        )


class CourseDefaultEnvironmentCreateView(
    LoginRequiredMixin,
    CourseBindingMixin,
    CourseEnvironmentTabMixin,
    View,
):
    def post(self, request, *args, **kwargs):
        course = self.get_course()
        presentation = self.get_presenter()

        if not presentation.can_create_environment:
            return HttpResponseForbidden(
                "You cannot create an environment "
                "for this course."
            )

        if presentation.has_environment_containers:
            return self.render_tab(
                course,
                presentation,
                error=(
                    "An environment already exists "
                    "for this course."
                ),
            )

        try:
            container = (
                create_default_course_environment(
                    course=course,
                    user=request.user,
                )
            )

        except CourseEnvironmentCreationError as error:
            return self.render_tab(
                course,
                presentation,
                error=str(error),
            )

        # Clear/reload because the presenter may have
        # cached environment_containers.
        self._course_presenter = None
        presentation = self.get_presenter()

        response = self.render_tab(
            course,
            presentation,
        )

        response["HX-Trigger"] = json.dumps({
            "kooplex-toast": {
                "message": (
                    f'Environment "{container.name}" '
                    "was created."
                ),
                "level": "success",
            },
        })

        return response
