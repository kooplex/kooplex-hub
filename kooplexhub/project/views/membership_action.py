import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView

from ..models import Project
from ..services.lifecycle import (
    delete_project,
    leave_project,
)
from ..services.project_presenter import ProjectPresenter


PROJECT_MEMBERSHIP_ACTION_MODAL_TEMPLATE = (
    "project/partials/membership_action_modal.html"
)


class ProjectMembershipActionView(
    LoginRequiredMixin,
    TemplateView,
):
    template_name = (
        PROJECT_MEMBERSHIP_ACTION_MODAL_TEMPLATE
    )
    pk_url_kwarg = "project_id"

    project = None
    presenter = None

    def get_project(self):
        if self.project is None:
            self.project = get_object_or_404(
                Project.objects
                .visible_to(self.request.user)
                .prefetch_related(
                    "userbindings__user",
                ),
                pk=self.kwargs[
                    self.pk_url_kwarg
                ],
            )

        return self.project

    def get_presenter(self):
        if self.presenter is None:
            self.presenter = ProjectPresenter(
                project=self.get_project(),
                user=self.request.user,
            )

        return self.presenter

    def require_available_action(self):
        presenter = self.get_presenter()

        if not (
            presenter.can_delete
            or presenter.can_leave
        ):
            raise PermissionDenied

        return presenter

    def get_context_data(
        self,
        **kwargs,
    ):
        context = super().get_context_data(
            **kwargs
        )

        presenter = self.require_available_action()

        context.update({
            "project": self.get_project(),
            "presentation": presenter,
        })

        return context

    def post(
        self,
        request,
        *args,
        **kwargs,
    ):
        presenter = self.require_available_action()
        project = self.get_project()

        if presenter.can_delete:
            result = delete_project(
                project=project,
                actor=request.user,
            )
        elif presenter.can_leave:
            result = leave_project(
                project=project,
                actor=request.user,
            )
        else:
            raise PermissionDenied

        response = HttpResponse(status=204)
        response["HX-Trigger"] = json.dumps({
            "modal-close": True,
            "project-list-refresh": {
                "projectId": result.project_id,
                "action": result.action,
            },
        })

        return response
