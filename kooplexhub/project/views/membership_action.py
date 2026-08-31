import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import (
    PermissionDenied,
    ValidationError,
)
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView

from ..models import Project
from ..services.lifecycle import (
    delete_project,
    leave_project,
    request_forced_project_delete,
)
from ..services.project_presenter import ProjectPresenter
from hub.services.http import toast_response


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
                    "containerbindings__container__user",
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

        action = request.POST.get(
            "action",
            "delete",
        )

        try:
            if presenter.can_delete:
                
                if action == "force-delete":
                    result = (
                        request_forced_project_delete(
                            project=project,
                            actor=request.user,
                        )
                    )

                elif action == "delete":
                    result = delete_project(
                        project=project,
                        actor=request.user,
                    )

                else:
                    raise ValidationError(
                        "Unknown project action."
                    )

            elif presenter.can_leave:
                result = leave_project(
                    project=project,
                    actor=request.user,
                )
            else:
                raise PermissionDenied
        except ValidationError as error:
            message = " ".join(
                error.messages
            )
    
            return toast_response(
                message,
                level="error",
            )
    
        except PermissionDenied as error:
            return toast_response(
                str(error),
                level="error",
            )

        response = HttpResponse(status=204)
        response["HX-Trigger"] = json.dumps({
            "modal-close": True,
            "project-list-refresh": {
                "projectId": result.project_id,
                "action": result.action,
            },
        })

        return response
