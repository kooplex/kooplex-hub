import json

from django.db.models import Q
from django.contrib.auth.mixins import (
    LoginRequiredMixin,
)
from django.views.generic import TemplateView
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.template.response import TemplateResponse
from django.views import View

from ..conf import PROJECT_SETTINGS
from ..services.project import (
    get_joinable_projects_for_user,
)
from ..models import UserProjectBinding
from ..forms.join import ProjectJoinForm
from ..services.lifecycle import join_project


PROJECT_JOIN_MODAL_TEMPLATE = (
    "project/partials/join/modal.html"
)
PROJECT_JOIN_LIST_TEMPLATE = (
    "project/partials/join/project_list.html"
)


def make_join_project_item(project):
    bindings = list(
        project.userbindings.all()
    )

    creator_binding = next(
        (
            binding
            for binding in bindings
            if binding.role
            == UserProjectBinding.Role.CREATOR
        ),
        None,
    )

    collaborator_bindings = [
        binding
        for binding in bindings
        if binding.role
        != UserProjectBinding.Role.CREATOR
    ]

    return {
        "project": project,
        "creator": (
            creator_binding.user
            if creator_binding is not None
            else None
        ),
        "collaborators": tuple(
            binding.user
            for binding in collaborator_bindings
        ),
        "collaborator_count": len(
            collaborator_bindings
        ),
    }


class ProjectJoinQueryMixin:
    search_limit = 50

    def get_query(self):
        return self.request.GET.get(
            "q",
            "",
        ).strip()

    def get_joinable_projects(self):
        projects = (
            get_joinable_projects_for_user(
                self.request.user
            )
        )

        query = self.get_query()

        if not query:
            return projects[:self.search_limit]

        matches = Q()

        for term in query.split():
            term_match = (
                Q(name__icontains=term)
                | Q(description__icontains=term)
                | Q(
                    userbindings__user__username__icontains=term
                )
                | Q(
                    userbindings__user__first_name__icontains=term
                )
                | Q(
                    userbindings__user__last_name__icontains=term
                )
            )

            matches &= term_match

        return (
            projects
            .filter(matches)
            .distinct()[:self.search_limit]
        )

    def get_join_project_items(self):
        return tuple(
            make_join_project_item(project)
            for project in self.get_joinable_projects()
        )

    def get_join_context(
        self,
        *,
        form,
    ):
        return {
            "form": form,
            "project_items": (
                self.get_join_project_items()
            ),
            "query": self.get_query(),
            "start_url": reverse(
                "project:start",
            ),
            "search_url": reverse(
                "project:join-search",
            ),
            "join_url": reverse(
                "project:join",
            ),
        }



class ProjectJoinModalView(
    LoginRequiredMixin,
    ProjectJoinQueryMixin,
    TemplateView,
):
    template_name = PROJECT_JOIN_MODAL_TEMPLATE

    def get_context_data(
        self,
        **kwargs,
    ):
        context = super().get_context_data(
            **kwargs
        )

        form = kwargs.get("form") or ProjectJoinForm(
            actor=self.request.user,
        )

        context.update(
            self.get_join_context(
                form=form,
            )
        )

        return context


class ProjectJoinSearchView(
    LoginRequiredMixin,
    ProjectJoinQueryMixin,
    TemplateView,
):
    template_name = PROJECT_JOIN_LIST_TEMPLATE

    def get_context_data(
        self,
        **kwargs,
    ):
        context = super().get_context_data(
            **kwargs
        )

        context.update({
            "project_items": (
                self.get_join_project_items()
            ),
            "query": self.get_query(),
        })

        return context


class ProjectJoinView(
    LoginRequiredMixin,
    ProjectJoinQueryMixin,
    View,
):
    http_method_names = ["post"]

    def post(
        self,
        request,
        *args,
        **kwargs,
    ):
        form = ProjectJoinForm(
            data=request.POST,
            actor=request.user,
        )

        if not form.is_valid():
            return TemplateResponse(
                request,
                PROJECT_JOIN_MODAL_TEMPLATE,
                {
                    "form": form,
                    "project_items": (
                        self.get_join_project_items()
                    ),
                    "query": "",
                    "start_url": reverse(
                        "project:start",
                    ),
                    "search_url": reverse(
                        "project:join-search",
                    ),
                    "join_url": reverse(
                        "project:join",
                    ),
                },
            )

        project = form.cleaned_data["project"]

        try:
            join_project(
                project=project,
                actor=request.user,
            )
        except ValidationError as error:
            form.add_error(
                "project",
                error,
            )

            return TemplateResponse(
                request,
                PROJECT_JOIN_MODAL_TEMPLATE,
                {
                    "form": form,
                    "project_items": (
                        self.get_join_project_items()
                    ),
                    "query": "",
                    "start_url": reverse(
                        "project:start",
                    ),
                    "search_url": reverse(
                        "project:join-search",
                    ),
                    "join_url": reverse(
                        "project:join",
                    ),
                },
            )

        response = HttpResponse(status=204)
        response["HX-Trigger"] = json.dumps({
            "modal-close": True,
            "project-list-refresh": {
                "projectId": project.pk,
                "action": "joined",
            },
        })

        return response



