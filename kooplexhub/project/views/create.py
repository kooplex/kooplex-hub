import logging
import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.views.generic import TemplateView
from django.views import View
from django.db import transaction

from project.forms.create import ProjectCreateForm
from project.models import UserProjectBinding
from container.services.image_catalog import ImageCatalogService

from ..services.editor_context import (
    make_membership_ui,
    make_create_image_editor_context,
    make_create_member_editor_context,
)
from ..services.creation import ProjectCreationService

logger = logging.getLogger(__name__)
User = get_user_model()

CREATE_PROJECT_MODAL_TEMPLATE = "project/partials/create/modal.html"


def get_selected_members_from_form(form):
    if form.is_bound:
        raw_user_ids = form.data.getlist("member_users")

        users = {
            str(user.pk): user
            for user in form.fields[
                "member_users"
            ].queryset.filter(pk__in=raw_user_ids)
        }

        selected_members = []

        for raw_user_id in raw_user_ids:
            user = users.get(str(raw_user_id))

            if user is None:
                continue

            selected_members.append({
                "user": user,
                "role": form.data.get(
                    f"member_role_{user.pk}",
                    UserProjectBinding.Role.COLLABORATOR,
                ),
            })

        return selected_members

    return []

class ProjectCreateContextMixin:
    def get_available_images(self):
        return ImageCatalogService.available_for_user(
            self.request.user
        )

    def get_available_member_users(self):
        return User.objects.exclude(
            pk=self.request.user.pk,
        ).order_by(
            "first_name",
            "last_name",
            "username",
        )


    def get_form(self, *, data=None):
        return ProjectCreateForm(
            data=data,
            actor=self.request.user,
            available_images=self.get_available_images(),
            available_users=self.get_available_member_users(),
            auto_id="project-create-%s",
        )


    def get_project_create_context(self, *, form): #FIXME: looks like unused
        selected_members = (
            get_selected_members_from_form(form)
        )

        return {
            "form": form,
            "image_editor": (
                make_create_image_editor_context(
                    form=form,
                )
            ),
            "membership_editor": (
                make_create_member_editor_context(
                    form=form,
                )
            ),
            "selected_mounts": [],
        }


class ProjectCreateModalView(
    LoginRequiredMixin,
    ProjectCreateContextMixin,
    TemplateView,
):
    template_name = CREATE_PROJECT_MODAL_TEMPLATE

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = kwargs.get("form") or self.get_form()
    
        context.update({
            "form": form,
            "image_editor": make_create_image_editor_context(
                form=form,
            ),
            "membership_editor": make_create_member_editor_context(
                form=form,
            ),
            "membership_ui": make_membership_ui(dom_id="project-create-members"),
        })
    
        return context



class ProjectCreateView(
    LoginRequiredMixin,
    ProjectCreateContextMixin,
    View,
):
    template_name = CREATE_PROJECT_MODAL_TEMPLATE

    def post(self, request, *args, **kwargs):
        form = self.get_form(data=request.POST)

        if not form.is_valid():
            return render(
                request,
                self.template_name,
                self.get_project_create_context(
                    form=form,
                ),
                status=422,
            )

        with transaction.atomic():
            result = ProjectCreationService.create(
                owner=request.user,
                name=form.cleaned_data["name"],
                scope=form.cleaned_data["scope"],
                description=form.cleaned_data["description"],
                preferred_image=form.cleaned_data["preferred_image"],
                members=form.cleaned_data["members"],
                mounts=[], #form.cleaned_data["mounts"],
                create_environment=(
                    form.cleaned_data["creation_mode"]
                    == "project_and_environment"
                ),
            )

        response = HttpResponse(status=204)
        response["HX-Trigger"] = json.dumps(
            {
                "modal-close": True,
            }
        )
        response["HX-Trigger-After-Settle"] = json.dumps(
            {
                "project-list-refresh": {
                    "projectId": result.project.pk,
                    "environmentId": (
                        result.environment.pk
                        if result.environment
                        else None
                    ),
                },
            }
        )

        return response
