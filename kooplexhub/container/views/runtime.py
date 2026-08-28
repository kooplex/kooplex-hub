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


from kooplexhub.lib import custom_redirect
from hub.services.live import (
    push_live_message,
)
from hub.services.http import (
    toast_response,
)
from ..models import Container
from ..services.lifecycle import (
    delete_container,
)
from ..services.live import (
    broadcast_container_runtime_changed,
)
from ..services.runtime_presenter import ContainerRuntimePresenter
from ..services.runtime_control import (
    ContainerActionError,
    request_container_action,
)
from ..services.runtime_query import (
    get_container_log,
)
from ..services.service_catalog import (
    get_container_service_view,
)
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

    template_names = {
        "start": (
            "container/partials/widgets/"
            "start_button.html"
        ),
        "stop": (
            "container/partials/widgets/"
            "stop_button.html"
        ),
        "restart": (
            "container/partials/widgets/"
            "restart_button.html"
        ),
    }

    def post(self, request, pk, action):
        if action not in self.allowed_actions:
            return toast_response(
                "Unknown environment action."
            )

        container = get_object_or_404(
            Container.objects.filter(
                user=request.user
            ),
            pk=pk,
        )

        try:
            result = request_container_action(
                container=container,
                action=action,
                actor=request.user,
            )
        except ContainerActionError as error:
            return toast_response(
                str(error),
                level="error",
            )

        # runtime_control locked/refetched another
        # model instance.
        container.refresh_from_db()

        broadcast_container_runtime_changed(
            container=container,
            reason=(
                f"container.{action}.requested"
            ),
        )

        response = render(
            request,
            self.template_names[action],
            {
                "container": container,
                "runtime": (
                    ContainerRuntimePresenter(
                        container
                    )
                ),
            },
        )

        response["HX-Trigger"] = json.dumps({
            "kooplex-toast": {
                "message": result.message,
                "level": result.level,
            },
        })

        return response


class ContainerOpenServiceView(
    LoginRequiredMixin,
    ContainerAccessMixin,
    View,
):
    def get(
        self, 
        request, 
        pk, 
        pk_view
    ):
        container = self.get_container()

        if not container.is_running:
            push_live_message(
                user=request.user,
                message=(
                    f"Cannot open {container.name}: "
                    f"{container.get_state_display()}"
                ),
                level="error",
            )
            return HttpResponse(
                "Environment is no longer running.",
                status=409,
            )

        service_view = (
            get_container_service_view(
                container,
                pk_view,
            )
        )

        if service_view is None:
            push_live_message(
                user=request.user,
                message=(
                    "The requested environment "
                    "view is no longer available."
                ),
                level="error",
            )
            return HttpResponse(
                "Service view is unavailable.",
                status=404,
            )

        url = service_view.url_substitute(
            container
        )

        if service_view.pass_token:
            return custom_redirect(
                url,
                token=(
                    container.user
                    .profile.token
                ),
            )

        return custom_redirect(url)


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

        container_id = delete_container(
            container=container,
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
            log_content = get_container_log(container)

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
