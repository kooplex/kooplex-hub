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

from .base import CourseEditorBaseView
from ...services.members import (
    ROLE_STUDENT,
    update_course_members,
)
from ...services.editor_context import (
    COURSE_MEMBERS_UPDATED_EVENT,
    make_member_editor_urls,
    make_membership_ui,
    make_member_summary_context,
)
from ...conf import EDUCATION_SETTINGS
from ...forms import CourseMembersForm
from ...models import UserCourseBinding



User = get_user_model()
logger = logging.getLogger(__name__)

MEMBERSHIP_SUMMARY_TEMPLATE = "ui/editors/membership/summary.html"
MEMBERSHIP_MODAL_TEMPLATE = "ui/editors/membership/modal.html"
MEMBERSHIP_SEARCH_RESULTS_TEMPLATE = "ui/editors/membership/search_results.html"
MEMBERSHIP_ROW_TEMPLATE = "ui/editors/membership/row.html"
MEMBERSHIP_EDIT_TEMPLATE = "ui/editors/membership/edit.html"


class CourseMembersBaseView(CourseEditorBaseView):
    field_name = None
    permission_name = "can_manage_members"
    editor_slug = "members"
    aria_label = "Manage course members"

    def get_membership_dom_id(self):
        return f"course-{self.get_course().pk}-members"

    def make_membership_ui(self):
        return make_membership_ui(
            dom_id=self.get_membership_dom_id(),
        )

    def get_form(self, *, data=None):
        course = self.get_course()

        return CourseMembersForm(
            data=data,
            actor=self.request.user,
            auto_id=(
                f"course-{course.pk}-members-%s"
            ),
        )

    def get_selected_members(
        self,
        *,
        form=None,
    ):
        if form is not None and form.is_bound:
            return tuple(
                member_selection_to_context(selection)
                for selection in (
                    form.cleaned_data.get(
                        "members",
                        (),
                    )
                    if form.is_valid()
                    else ()
                )
            )

        return tuple(
            make_course_member_presentation(
                binding=binding,
            )
            for binding in (
                self.get_course()
                .userbindings
                .select_related("user")
                .exclude(user=self.request.user)
                .order_by(
                    "-is_teacher",
                    "user__username",
                )
            )
        )

    def get_editor_urls(self):
        return make_member_editor_urls(
            self.get_course()
        )

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
            "refresh_event": (
                COURSE_MEMBERS_UPDATED_EVENT
            ),
            "title": "Manage course members",
        })

        return context


class CourseMembersSummaryView(
    CourseMembersBaseView
):
    template_name = MEMBERSHIP_SUMMARY_TEMPLATE

    def get_context_data(
        self,
        **kwargs,
    ):
        course = self.get_course()
        presentation = self.get_presenter()
        return {
            "editor": make_member_summary_context(
                course=course, 
                presenter=presentation,
            ),
        }


class CourseMembersModalView(
    CourseMembersBaseView,
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


class CourseMembersChangeView(
    CourseMembersBaseView
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

class CourseMembersUpdateView(
    CourseMembersBaseView
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

        course = self.get_course()
        changes = update_course_members(
            course=course,
            actor=request.user,
            members=form.cleaned_data[
                "members"
            ],
        )

        if changes.changed:
            logger.info(
                "Course %s memberships changed by %s: "
                "%d added, %d updated, %d removed",
                course.pk,
                request.user.pk,
                len(changes.added),
                len(changes.updated),
                len(changes.removed),
            )

        response = HttpResponse(status=204)

        response["HX-Trigger"] = json.dumps(
            {
                "modal-close": True,
                COURSE_MEMBERS_UPDATED_EVENT: {
                    "course_id": course.pk,
                },
            }
        )

        return response



class MemberSearchCore:
    minimum_query_length = (
        EDUCATION_SETTINGS
        .membership_editor
        .minimum_query_length
    )
    limit = (
        EDUCATION_SETTINGS
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


class CourseMemberSearchView(
    MemberSearchCore,
    CourseMembersBaseView,
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
            self.get_course()
            .userbindings
            .values_list(
                "user_id",
                flat=True,
            )
        )

        return excluded_user_ids

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        course = self.get_course()
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
                    "education:member-row",
                    kwargs={
                        "course_id": course.pk,
                        "user_id": user.pk,
                    },
                ),
            }
            for user in self.search_users()
            ]

        return context


class CourseCreateMemberSearchView(
    MemberSearchCore,
    CourseMembersBaseView,
):
    template_name = MEMBERSHIP_SEARCH_RESULTS_TEMPLATE
    membership_dom_id = "course-create-members"

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
                    "education:create-member-row",
                    kwargs={
                        "user_id": user.pk,
                    },
                ),
            }
            for user in self.search_users()
        ]
        return context


class CourseMemberRowView(
    CourseMembersBaseView
):
    template_name = MEMBERSHIP_ROW_TEMPLATE

    def get(self, request, course_id, user_id):
        course = self.get_course()
        presentation = self.get_presenter()

        if not presentation.can_manage_members:
            return HttpResponseForbidden()

        user = get_object_or_404(
            User.objects.filter(is_active=True),
            pk=user_id,
        )
        binding = (
            UserCourseBinding.objects
            .filter(
                course=course,
                user=user,
            )
            .only("is_teacher")
            .first()
        )
        
        role = (
            binding.role
            if binding is not None
            else ROLE_STUDENT
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


class CourseCreateMemberRowView(
    CourseMembersBaseView
):
    template_name = MEMBERSHIP_ROW_TEMPLATE
    membership_dom_id = "course-create-members"

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
                "role": ROLE_STUDENT,
            },
        })

        return context
