import json
import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.core.exceptions import PermissionDenied
from django.template.response import TemplateResponse
from django.http import HttpResponse
from django.shortcuts import (
    render,
    get_object_or_404,
)
from django.urls import reverse
from django.views import View
from django.views.generic import ListView

from .base import ProjectEditorBaseView
from ..mixins import ProjectMemberAccessMixin
from ...services.members import update_project_members
from ...services.editor_context import (
    make_membership_ui,
    make_member_editor_context,
    make_member_summary_context,
)
from ...conf import PROJECT_SETTINGS
from ...forms import ProjectMembersForm
from ...models import UserProjectBinding

User = get_user_model()
logger = logging.getLogger(__name__)

MEMBERSHIP_SUMMARY_TEMPLATE = "ui/editors/membership/summary.html"
MEMBERSHIP_MODAL_TEMPLATE = "ui/editors/membership/modal.html"
MEMBERSHIP_SEARCH_RESULTS_TEMPLATE = "ui/editors/membership/search_results.html"
MEMBERSHIP_ROW_TEMPLATE = "ui/editors/membership/row.html"
MEMBERSHIP_EDIT_TEMPLATE = "ui/editors/membership/edit.html"


class ProjectMembersBaseView(ProjectEditorBaseView):
    field_name = None
    permission_name = "can_manage_members"
    editor_slug = "members"
    aria_label = "Manage project members"

    def get_membership_dom_id(self):
        return self.make_editor_context()[
            "dom_id"
        ]

    def make_membership_ui(self):
        return make_membership_ui(
            dom_id=self.get_membership_dom_id(),
        )

    def get_form(self, *, data=None):
        project = self.get_project()

        return ProjectMembersForm(
            data=data,
#            project=self.get_project(),
            actor=self.request.user,
            auto_id=(
                f"project-{project.pk}"
                "-collaborators-%s"
            ),
        )

    def get_selected_members(
        self,
        *,
        form=None,
    ):
        if form is not None and form.is_bound:
            return form.get_selected_members()

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

    def get_editor_urls(self):
        urls = super().get_editor_urls()

        project = self.get_project()
        kwargs = {
            "project_id": project.pk,
        }

        urls.update({
            "search_url": reverse(
                "project:members-search",
                kwargs=kwargs,
            ),
        })

        return urls

    def extend_editor_context(
        self,
        context,
        *,
        form=None,
    ):
        context.update({
            "selected_members": (
                self.get_selected_members(
                    form=form,
                )
            ),
            "staged": False,
        })

        return context


class ProjectMembersSummaryView(
    ProjectMembersBaseView
):
    template_name = MEMBERSHIP_SUMMARY_TEMPLATE

    def get_context_data(
        self,
        **kwargs,
    ):
        project = self.get_project()
        presentation = self.get_presenter()
        return {
            "editor": make_member_summary_context(
                project=project, 
                presenter=presentation,
            ),
        }


class ProjectMembersModalView(
    ProjectMembersBaseView,
):
    template_name = MEMBERSHIP_MODAL_TEMPLATE

    def get_context_data(self, **kwargs):
        self.require_edit_permission()

        form = (
            kwargs.get("form")
            or self.get_form()
        )

        return {
            "editor": self.make_editor_context(),
            "membership_ui": self.make_membership_ui(),
        }


class ProjectMembersChangeView(
    ProjectMembersBaseView
):
    template_name = MEMBERSHIP_EDIT_TEMPLATE

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

class ProjectMembersUpdateView(
    ProjectMembersBaseView
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
                MEMBERSHIP_EDIT_TEMPLATE,
                {
                    "editor": (
                        self.make_editor_context(
                            form=form,
                        )
                    ),
                },
                status=422,
            )

        project = self.get_project()
        changes = update_project_members(
            project=project,
            actor=request.user,
            members=form.cleaned_data[
                "members"
            ],
        )

        if changes.changed:
            logger.info(
                "Project %s memberships changed by %s: "
                "%d added, %d updated, %d removed",
                project.pk,
                request.user.pk,
                len(changes.added),
                len(changes.updated),
                len(changes.removed),
            )

        response = HttpResponse(status=204)

        response["HX-Trigger"] = json.dumps(
            {
                "modal-close": True,
                "project-members-updated": {
                    "project_id": project.pk,
                },
            }
        )

        return response



class MemberSearchCore:
    minimum_query_length = (
        PROJECT_SETTINGS
        .membership_editor
        .minimum_query_length
    )
    limit = (
        PROJECT_SETTINGS
        .membership_editor
        .search_limit
    )

    def get_search_query(self):
        return self.request.GET.get("q", "").strip()

    def get_selected_user_ids(self):
        return {
            int(user_id)
            for user_id in self.request.GET.getlist(
                "member_users"
            )
            if user_id.isdigit()
        }

    def get_excluded_user_ids(self):
        return {
            self.request.user.pk,
            *self.get_selected_user_ids(),
        }

    def search_users(self):
        query = self.get_search_query()
        if len(query) < self.minimum_query_length:
            return User.objects.none()

        matches = Q()
        for term in query.split():
            term_match = (
                Q(username__icontains=term)
                | Q(first_name__icontains=term)
                | Q(last_name__icontains=term)
            )
            matches &= term_match

        excluded_user_ids = (
            self.get_excluded_user_ids()
        )

        return (
            User.objects
            .filter(
                is_active=True
            )
            .filter(matches)
            .exclude(
                pk__in=excluded_user_ids,
            )
            .order_by("username")[:self.limit]
        )


class ProjectMemberSearchView(
    MemberSearchCore,
    ProjectMembersBaseView,
):
    template_name = MEMBERSHIP_SEARCH_RESULTS_TEMPLATE

    def dispatch(
        self,
        request,
        *args,
        **kwargs,
    ):
        self.require_edit_permission()

        return super().dispatch(
            request,
            *args,
            **kwargs,
        )

    def get_excluded_user_ids(self):
        excluded_user_ids = (
            super().get_excluded_user_ids()
        )

        excluded_user_ids.update(
            self.get_project()
            .userbindings
            .values_list(
                "user_id",
                flat=True,
            )
        )

        return excluded_user_ids

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        project = self.get_project()
        query = self.get_search_query()

        context.update(
            {
                "membership_ui": self.make_membership_ui(),
                "minimum_query_length": self.minimum_query_length,
                "query": query,
                "query_too_short": (
                    len(query)
                    < self.minimum_query_length
                ),
                "search_results": [],
            }
        )

        if context["query_too_short"]:
            return context

        context["search_results"] = [
            {
                "user": user,
                "row_url": reverse(
                    "project:member-row",
                    kwargs={
                        "project_id": project.pk,
                        "user_id": user.pk,
                    },
                ),
            }
            for user in self.search_users()
            ]

        return context


class ProjectCreateMemberSearchView(
    MemberSearchCore,
    ProjectMembersBaseView,
):
    template_name = MEMBERSHIP_SEARCH_RESULTS_TEMPLATE
    membership_dom_id = "project-create-members"

    def get_membership_dom_id(self):
        return self.membership_dom_id

    def get_context_data(self, **kwargs):
        query = self.get_search_query()
        context = super().get_context_data(**kwargs)

        context.update(
            {
                "query": query,
                "membership_ui": self.make_membership_ui(),
                "minimum_query_length": (
                    self.minimum_query_length
                ),
                "query_too_short": (
                    len(query)
                    < self.minimum_query_length
                ),
                "staged": True,
                "search_results": [],
            }
        )

        if context["query_too_short"]:
            return context

        context["search_results"] = [
            {
                "user": user,
                "row_url": reverse(
                    "project:create-member-row",
                    kwargs={
                        "user_id": user.pk,
                    },
                ),
            }
            for user in self.search_users()
        ]
        return context


class ProjectMemberRowView(
    ProjectMembersBaseView
):
    template_name = MEMBERSHIP_ROW_TEMPLATE

    def get(self, request, project_id, user_id):
        project = self.get_project()
        presentation = self.get_presenter()

        if not presentation.can_manage_members:
            return HttpResponseForbidden()

        user = get_object_or_404(
            User.objects.filter(is_active=True),
            pk=user_id,
        )
        binding = (
            UserProjectBinding.objects
            .filter(
                project=project,
                user=user,
            )
            .only("role")
            .first()
        )
        
        role = (
            binding.role
            if binding is not None
            else UserProjectBinding.Role.COLLABORATOR
        )

        editor = self.make_editor_context()
        return render(
            request,
            self.template_name,
            {
                "membership_ui": self.make_membership_ui(),
                "member": {
                    "user": user,
                    "role": role,
                },
            },
        )


class ProjectCreateMemberRowView(
    ProjectMembersBaseView
):
    template_name = MEMBERSHIP_ROW_TEMPLATE
    membership_dom_id = "project-create-members"

    def get_membership_dom_id(self):
        return self.membership_dom_id

    def get_context_data(
        self,
        **kwargs,
    ):
        context = super().get_context_data(
            **kwargs
        )

        user = get_object_or_404(
            User.objects.filter(
                is_active=True,
            ),
            pk=self.kwargs["user_id"],
        )


        context.update({
            "membership_ui": self.make_membership_ui(),
            "member": {
                "user": user,
                "role": (
                    UserProjectBinding
                    .Role
                    .COLLABORATOR
                ),
            },
        })

        return context
