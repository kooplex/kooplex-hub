import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, render
from django.views import View

from project.models import Project
from project.services.environments import (
    ProjectEnvironmentCreationError,
    create_default_project_environment,
)
from project.services.project_presenter import ProjectPresenter
#FIXME from project.services.live import broadcast_project_live_event


class ProjectEnvironmentTabMixin:
    template_name = "project/partials/tabs/environment.html"

    def get_project(self):
        return get_object_or_404(
            Project.objects
            .visible_to(self.request.user)
            .select_related("preferred_image")
            .prefetch_related(
                "containerbindings__container__image",
                "volumebindings__volume",
                "userbindings__user",
            ),
            pk=self.kwargs["pk"],
        )

    def render_tab(self, project, **extra):
        presentation = ProjectPresenter(
            project=project,
            user=self.request.user,
        )

        return render(
            self.request,
            self.template_name,
            {
                "project": project,
                "presentation": presentation,
                **extra,
            },
        )


class ProjectEnvironmentTabView(
    LoginRequiredMixin,
    ProjectEnvironmentTabMixin,
    View,
):
    def get(self, request, pk):
        return self.render_tab(self.get_project())


class ProjectDefaultEnvironmentCreateView(
    LoginRequiredMixin,
    ProjectEnvironmentTabMixin,
    View,
):
    def post(self, request, pk):
        project = self.get_project()

        presentation = ProjectPresenter(
            project=project,
            user=request.user,
        )

        if not presentation.can_create_environment:
            return HttpResponseForbidden(
                "You cannot create an environment for this project."
            )

        if presentation.has_environment_containers:
            return self.render_tab(
                project,
                error="An environment already exists for this project.",
            )

        try:
            container = create_default_project_environment(
                project=project,
                user=request.user,
            )
        except ProjectEnvironmentCreationError as error:
            return self.render_tab(
                project,
                error=str(error),
            )

        # Reload prefetched relationships after creation.
        project = self.get_project()

#        broadcast_project_live_event(
#            user=request.user,
#            keys=[
#                f"project-environments:{project.pk}",
#            ],
#            payload={
#                "event": "project.environment.created",
#                "model": "project",
#                "id": project.pk,
#                "container_id": container.pk,
#            },
#        )

        response = self.render_tab(project)

        response["HX-Trigger"] = json.dumps(
            {
                "kooplex-toast": {
                    "message": (
                        f'Environment "{container.name}" was created.'
                    ),
                    "level": "success",
                },
            }
        )

        return response
