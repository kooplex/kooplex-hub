from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.views.generic import TemplateView

from ..conf import PROJECT_SETTINGS
from ..services.project import (
    get_joinable_projects_for_user,
)


PROJECT_START_MODAL_TEMPLATE = (
    "project/partials/start/modal.html"
)


class ProjectStartView(
    LoginRequiredMixin,
    TemplateView,
):
    template_name = PROJECT_START_MODAL_TEMPLATE

    def get_joinable_projects(self):
        return get_joinable_projects_for_user(
            self.request.user
        )

    def get(self, request, *args, **kwargs):
        joinable_projects = (
            self.get_joinable_projects()
        )

        if (
            PROJECT_SETTINGS
            .skip_workflow_chooser_when_no_joinable_project
            and not joinable_projects.exists()
        ):
            return redirect(
                "project:create-modal",
            )

        self.joinable_projects = joinable_projects

        return super().get(
            request,
            *args,
            **kwargs,
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(
            **kwargs
        )

        projects = getattr(
            self,
            "joinable_projects",
            self.get_joinable_projects(),
        )

        context.update({
            "joinable_project_count": (
                projects.count()
            ),
            "has_joinable_projects": (
                projects.exists()
            ),
        })

        return context



