import logging
import json

from django.http import HttpResponse
from django.views.generic import (
    View,
    TemplateView,
)
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import (
    get_object_or_404, 
    render, 
    redirect,
)

from ..models import Container
from ..services.live import (
    broadcast_container_runtime_changed,
    broadcast_container_live_event,
)
from ..services.runtime_presenter import ContainerRuntimePresenter
from .mixins import (
    ContainerAccessMixin,
    ContainerRuntimePartialMixin,
)


logger = logging.getLogger(__name__)


class ContainerControlView(
    LoginRequiredMixin,
    ContainerRuntimePartialMixin,
    View,
):
    allowed_actions = {
        "start",
        "stop",
        "restart",
    }

    def post(self, request, pk, action):
        if action not in self.allowed_actions:
            return render(
                request,
                "error.html",
                {"message": "Unknown container action."},
                status=400,
            )

        container = get_object_or_404(
            Container.objects.filter(user=request.user),
            pk=pk,
        )

        if action == "start":
            container.start()
            message = f"Starting environment '{container.name}'."
            level = "success"
            template_name = "container/partials/widgets/start_button.html"

        elif action == "stop":
            container.stop()
            message = f"Stopping environment '{container.name}'."
            level = "warning"
            template_name = "container/partials/widgets/stop_button.html"

        else:
            container.restart()
            message = f"Restarting environment '{container.name}'."
            level = "warning"
            template_name = "container/partials/widgets/restart_button.html"

        broadcast_container_runtime_changed(
            container=container,
            actor=request.user,
            reason=f"container.{action}.requested",
        )

        response = render(
            request,
            template_name,
            {
                "container": container,
                "runtime": ContainerRuntimePresenter(container),
            },
        )

        response["HX-Trigger"] = json.dumps(
            {
                "kooplex-toast": {
                    "message": message,
                    "level": level,
                },
            }
        )

        return response


class ContainerOpenServiceView(
    LoginRequiredMixin,
    ContainerAccessMixin,
    View,
):
    def get(self, request, pk, pk_view):
        container = self.get_container()

        if not container.is_running:
            messages.error(
                request,
                f"Cannot open {container.name}: "
                f"{container.get_state_display()}",
            )
            return redirect("container:list")

        available_views = {
            view.pk: view
            for view in container.views
        }

        if pk_view not in available_views:
            messages.error(
                request,
                "The requested environment view is not available.",
            )
            return redirect("container:list")

        return container.redirect(pk_view)


class ContainerDeleteView(
    LoginRequiredMixin,
    ContainerAccessMixin,
    View,
):
    def post(self, request, pk):
        container = self.get_container()

        container_id = container.pk
        container_name = container.name
        user_id = request.user.pk

        logger.debug("Deleting container %s", container)

        container.delete()

        broadcast_container_live_event(
            user=request.user,
            keys=[
                f"container-list:user:{user_id}",
            ],
            payload={
                "event": "object.deleted",
                "model": "container",
                "id": container_id,
            },
        )

        if request.headers.get("HX-Request") == "true":
            response = HttpResponse(status=204)
            response["HX-Trigger"] = (
                '{"container-list-refresh": true, '
                '"kooplex-toast": {'
                f'"message": "Environment \\"{container_name}\\" was deleted.", '
                '"level": "success"}}'
            )
            return response

        return redirect("container:list")


class ContainerFetchlogButtonPartialView(
    LoginRequiredMixin,
    ContainerRuntimePartialMixin,
    TemplateView,
):
    template_name = "container/partials/widgets/fetchlog_button.html"

    def get_context_data(self, **kwargs):
        return self.get_runtime_context()


class ContainerFetchLogModalView(
    LoginRequiredMixin,
    ContainerAccessMixin,
    View,
):
    template_name = "container/partials/fetchlog_modal.html"

    def get(self, request, pk):
        container = self.get_container()

        return render(
            request,
            self.template_name,
            {
                "container": container,
            },
        )


class ContainerFetchLogView(
    LoginRequiredMixin,
    ContainerAccessMixin,
    View,
):
    template_name = "container/partials/fetchlog_content.html"

    def get(self, request, pk):
        container = self.get_container()

        if not container.is_running:
            return render(
                request,
                self.template_name,
                {
                    "container": container,
                    "error": (
                        f"Logs cannot be retrieved while the environment is "
                        f"{container.get_state_display().lower()}"
                    ),
                },
                status=409,
            )

        try:
            log_content = container.retrieve_log()

        except Exception:
            logger.exception(
                "Failed to retrieve log for container %s",
                container.pk,
            )

            return render(
                request,
                self.template_name,
                {
                    "container": container,
                    "error": "The environment log could not be retrieved.",
                },
                status=502,
            )

        return render(
            request,
            self.template_name,
            {
                "container": container,
                "log_content": log_content,
            },
        )
