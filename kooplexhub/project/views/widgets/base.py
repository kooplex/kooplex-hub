import logging

from django.urls import reverse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView

from ...services.project_presenter import ProjectPresenter
from ...models import Project

logger = logging.getLogger(__name__)


class ProjectEditorBaseView(
    LoginRequiredMixin,
    TemplateView,
):
    pk_url_kwarg = "project_id"

    project = None
    presenter = None

    field_name = None
    permission_name = None
    editor_slug = None
    aria_label = None

    def get_project(self):
        if self.project is None:
            self.project = get_object_or_404(
                Project.objects
                .visible_to(self.request.user)
                .prefetch_related("userbindings__user"),
                pk=self.kwargs[self.pk_url_kwarg],
            )

        return self.project

    def get_presenter(self):
        if self.presenter is None:
            self.presenter = ProjectPresenter(
                project=self.get_project(),
                user=self.request.user,
            )

        return self.presenter

    def require_edit_permission(self):
        presenter = self.get_presenter()

        if not getattr(presenter, self.permission_name):
            raise PermissionDenied

        return presenter

    def get_editor_urls(self):
        project = self.get_project()
        kwargs = {"project_id": project.pk}

        return {
            "edit_url": reverse(
                f"project:{self.editor_slug}-edit",
                kwargs=kwargs,
            ),
            "display_url": reverse(
                f"project:{self.editor_slug}-display",
                kwargs=kwargs,
            ),
            "update_url": reverse(
                f"project:{self.editor_slug}-update",
                kwargs=kwargs,
            ),
        }

    def get_editor_value(self):
        if self.field_name is None:
            return None

        return getattr(
            self.get_project(),
            self.field_name,
        )

    def get_editor_field(self, *, form=None):
        if form is None or self.field_name is None:
            return None

        return form[self.field_name]

    def extend_editor_context(
        self,
        context,
        *,
        form=None,
    ):
        return context

    def make_editor_context(self, *, form=None):
        project = self.get_project()
        presenter = self.get_presenter()

        context = {
            "dom_id": (
                f"project-{project.pk}-"
                f"{self.editor_slug}"
            ),
            "value": self.get_editor_value(),
            "field": self.get_editor_field(
                form=form,
            ),
            "form": form,
            "can_edit": getattr(
                self.get_presenter(),
                self.permission_name,
            ),
            "aria_label": self.aria_label,
            **self.get_editor_urls(),
        }

        return self.extend_editor_context(
            context,
            form=form,
        )

    def refresh_editor_state(self, project):
        self.project = project
        self.presenter = None

