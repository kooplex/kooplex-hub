import json
import logging

#from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import get_user_model
#from django.db.models import Q
#from django.core.exceptions import PermissionDenied
#from django.template.response import TemplateResponse
#from django.shortcuts import (
#    render,
#    get_object_or_404,
#)
#from django.urls import reverse
#from django.views import View
#from django.views.generic import ListView
#
from .base import ProjectEditorBaseView
#from ..mixins import ProjectMemberAccessMixin
#from ...services.members import update_project_members
#from ...services.editor_context import make_member_editor_context
#from ...conf import PROJECT_SETTINGS
#from ...forms import ProjectMembersForm
#from ...models import UserProjectBinding
#
User = get_user_model()
logger = logging.getLogger(__name__)

MOUNTS_DISPLAY_TEMPLATE = "ui/editors/mounts_picker/display.html"
#MEMBERSHIP_SEARCH_TEMPLATE = "ui/editors/membership/search_results.html"
#MEMBERSHIP_MEMBER_ROW_TEMPLATE = "ui/editors/membership/row.html"
MOUNTS_EDIT_TEMPLATE = "ui/editors/mounts_picker/edit.html"
#
#COLLABORATION_TEMPLATE = "project/partials/tabs/collaboration.html"
#
#def get_assignable_member_role_choices():
#    return [
#        {
#            "value": value,
#            "label": label,
#        }
#        for value, label in (
#            UserProjectBinding
#            .Role
#            .assignable_choices()
#        )
#    ]


class ProjectMountsBaseView(ProjectEditorBaseView):
    field_name = None
    permission_name = "can_manage_mounts"
    editor_slug = "mounts"
    aria_label = "Manage project mounts"

    def get_form(self, *, data=None):
        project = self.get_project()

        return ProjectMountsForm(
            data=data,
#            project=self.get_project(),
            actor=self.request.user,
            auto_id=(
                f"project-{project.pk}"
                "-mounts-%s"
            ),
        )

    def get_selected_mounts(
        self,
        *,
        form=None,
    ):
        if form is not None and form.is_bound:
            return form.get_selected_mounts()

        return [
            {
                "user": binding.user,
                "role": binding.role,
            }
            for binding in (
                self.get_project()
                .userbindings
                .select_related("user")
                .exclude(
                    role=(
                        UserProjectBinding
                        .Role
                        .CREATOR
                    )
                )
            )
        ]

    def extend_editor_context(
        self,
        context,
        *,
        form=None,
    ):
        context.update({
            "selected_mounts": (
                self.get_selected_mounts(
                    form=form,
                )
            ),
            "staged": False,
        })

        return context


class ProjectMountsDisplayView(
    ProjectMountsBaseView
):
    template_name = MOUNTS_DISPLAY_TEMPLATE

    def get_context_data(
        self,
        **kwargs,
    ):
        return {
            "editor": self.make_editor_context(),
        }


class ProjectMountsChangeView(
    ProjectMountsBaseView
):
    template_name = MOUNTS_EDIT_TEMPLATE

    def get_context_data(
        self,
        **kwargs,
    ):
        self.require_edit_permission()

        form = (
            kwargs.get("form")
            or self.get_form()
        )

        return {
            "editor": self.make_editor_context(
                form=form,
            ),
        }

class ProjectMountsUpdateView(
    ProjectMountsBaseView
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
                MOUNTS_EDIT_TEMPLATE,
                {
                    "editor": (
                        self.make_editor_context(
                            form=form,
                        )
                    ),
                },
                status=422,
            )

        changes = update_project_members(
            project=self.get_project(),
            actor=request.user,
            members=form.cleaned_data[
                "members"
            ],
        )

        if changes.changed:
            logger.info(
                "Project %s memberships changed by %s: "
                "%d added, %d updated, %d removed",
                self.get_project().pk,
                request.user.pk,
                len(changes.added),
                len(changes.updated),
                len(changes.removed),
            )

        self.project = None
        self.presenter = None

        editor = self.make_editor_context()

        response = TemplateResponse(
            request,
            MOUNTS_DISPLAY_TEMPLATE,
            {
                "editor": editor,
            },
        )

        response["HX-Retarget"] = (
            f"#{editor['dom_id']}"
        )
        response["HX-Reswap"] = "outerHTML"
        response["HX-Trigger"] = json.dumps({
            "closeModal": {
                "modalId": (
                    f"{editor['dom_id']}-modal"
                ),
            },
        })

        return response


