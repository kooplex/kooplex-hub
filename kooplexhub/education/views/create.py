import json

from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import render
from django.views import View
from django.views.generic import TemplateView

from container.services.image_catalog import ImageCatalogService
from volume.models import Volume

from ..forms.create import CourseCreateForm
from ..services.lifecycle import CourseCreationService
from ..services.editor_context import (
    make_create_image_editor_context,
    make_create_member_editor_context,
    make_membership_ui,
    make_create_mounts_editor_context,
)


User = get_user_model()

CREATE_COURSE_MODAL_TEMPLATE = (
    "education/course/partials/create/modal.html"
)


class CourseCreateContextMixin:

    def check_create_permission(self):
        if not self.request.user.profile.can_createcourse:
            raise PermissionDenied

    def get_available_images(self):
        return ImageCatalogService.available_for_user(
            self.request.user
        )

    def get_available_member_users(self):
        return (
            User.objects
            .exclude(pk=self.request.user.pk)
            .order_by(
                "first_name",
                "last_name",
                "username",
            )
        )

    def get_available_volumes(self):
        return Volume.objects.visible_to(
            self.request.user
        )

    def get_form(self, *, data=None):
        return CourseCreateForm(
            data=data,
            actor=self.request.user,
            available_images=self.get_available_images(),
            available_users=self.get_available_member_users(),
            available_volumes=self.get_available_volumes(),
            auto_id="course-create-%s",
        )

    def get_create_context(self, *, form):
        return {
            "form": form,

            # Fill these using the same generic UI editor
            # helpers that Project uses:
            "image_editor": (
                make_create_image_editor_context(form=form)
            ),
            "membership_editor": (
                make_create_member_editor_context(form=form)
            ),
            "membership_ui": (
                make_membership_ui(
                    dom_id="course-create-members",
                )
            ),
            "mounts_editor": (
                make_create_mounts_editor_context(form=form)
            ),
        }


class CourseCreateModalView(
    LoginRequiredMixin,
    CourseCreateContextMixin,
    TemplateView,
):
    template_name = CREATE_COURSE_MODAL_TEMPLATE

    def get(self, request, *args, **kwargs):
        self.check_create_permission()
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        form = kwargs.get("form") or self.get_form()
        return self.get_create_context(form=form)


class CourseCreateView(
    LoginRequiredMixin,
    CourseCreateContextMixin,
    View,
):
    template_name = CREATE_COURSE_MODAL_TEMPLATE

    def post(self, request, *args, **kwargs):
        self.check_create_permission()

        form = self.get_form(data=request.POST)

        if not form.is_valid():
            return render(
                request,
                self.template_name,
                self.get_create_context(form=form),
                status=422,
            )

        result = CourseCreationService.create(
            owner=request.user,
            name=form.cleaned_data["name"],
            description=form.cleaned_data["description"],
            preferred_image=(
                form.cleaned_data["preferred_image"]
            ),
            members=form.cleaned_data["members"],
            mounts=form.cleaned_data["mounts"],
            create_environment=(
                form.cleaned_data["creation_mode"]
                == "course_and_environment"
            ),
        )

        response = HttpResponse(status=204)

        response["HX-Trigger"] = json.dumps({
            "modal-close": True,
            "course-list-refresh": {
                "courseId": result.course.pk,
                "environmentId": (
                    result.environment.pk
                    if result.environment
                    else None
                ),
            },
        })

        return response
