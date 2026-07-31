from django.shortcuts import get_object_or_404

from ..models import Project
from ..services.project_presenter import ProjectPresenter



class ProjectMemberAccessMixin:
    def get_project(self):
        return get_object_or_404(
            Project.objects
            .visible_to(self.request.user)
            .prefetch_related("userbindings__user"),
            pk=self.kwargs["pk"],
        )

    def get_presentation(self, project):
        return ProjectPresenter(
            project=project,
            user=self.request.user,
        )

