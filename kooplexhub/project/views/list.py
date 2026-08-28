import logging

from django.views.generic import (
    ListView,
    DetailView,
)
from django.contrib.auth.mixins import LoginRequiredMixin

from container.conf import CONTAINER_SETTINGS
from ..models import Project


logger = logging.getLogger(__name__)


class ProjectListView(
    LoginRequiredMixin, 
    ListView,
):
    model = Project
    template_name = 'project/list.html'
    context_object_name = 'projects'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            "page_title": "Environments",  #FIXME
            "page_eyebrow": "Workspace management",
            "page_description": "Create and manage your notebook environments.",
            "documentation_url": "https://xwiki.vo.elte.hu/en/kooplex-manual/projects",
            "project_page_config": {
                "userid": self.request.user.id,
                "configure_request": "configure-project",
                "model": "project",
                "required": ["name", "description", "preferred_image"],
            },
        })
        return context

    def get_queryset(self):
        return (
            Project.objects
            .visible_to(user=self.request.user)
            .select_related("preferred_image")
            .prefetch_related(
                "userbindings__user",
                "volumebindings__volume",
                "containerbindings__container__image",
            )
            .order_by("name")
        )


class ProjectGridView(
    LoginRequiredMixin, 
    ListView,
):
    template_name = "project/partials/grid.html"
    context_object_name = "projects"
    model = Project

    def get_queryset(self):
        return (
            Project.objects
            .visible_to(user=self.request.user)
            .select_related("preferred_image")
            .prefetch_related(
                "userbindings__user",
                "volumebindings__volume",
                "containerbindings__container__image",
            )
            .order_by("name")
        )


class ProjectCardPartialView(
    LoginRequiredMixin, 
    DetailView,
):
    model = Project
    template_name = "project/partials/card_wrapper.html"
    context_object_name = "project"

    def get_queryset(self):
        return (
            Project.objects
            .visible_to(user=self.request.user)
            .select_related("preferred_image")
            .prefetch_related(
                "userbindings__user",
                "volumebindings__volume",
                "containerbindings__container__image",
            )
        )

