import logging
import json

from django.views.generic import (
    View,
    TemplateView,
)
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import (
    get_object_or_404, 
    render, 
)

from .mixins import MountSelectionMixin
from ..models import Container
from ..forms import ContainerImageForm
from ..services.live import (
    broadcast_container_runtime_changed,
)
from ..services.image_catalog import ImageCatalogService
from ..services.runtime_control import (
    mark_container_restart_required,
)
from ..services.mounts import (
    apply_container_mounts, 
    mount_change_message,
    get_current_container_mount_ids,
)


logger = logging.getLogger(__name__)

IMAGE_PICKER_EDITOR_TEMPLATE = "ui/editors/image_picker/editor.html"

IMAGE_MODAL_TEMPLATE = "container/partials/image_modal.html"
MOUNTS_MODAL_TEMPLATE = "container/partials/mounts_modal.html"
CARD_WRAPPER_TEMPLATE = "container/partials/card_wrapper.html"

class ContainerImageModalView(
    LoginRequiredMixin, 
    TemplateView,
):
    template_name = IMAGE_MODAL_TEMPLATE

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        container = get_object_or_404(
            Container.objects.filter(user=self.request.user),
            pk=self.kwargs["pk"],
        )

        context.update(
            {
                "container": container,
                "form": ContainerImageForm(
                    instance=container,
                    user=self.request.user,
                ),
            }
        )

        return context


class ContainerImageSaveView(
    LoginRequiredMixin, 
    View,
):
    def post(self, request, pk):
        container = get_object_or_404(
            Container.objects.filter(user=request.user),
            pk=pk,
        )

        form = ContainerImageForm(
            request.POST,
            instance=container,
            user=request.user,
        )

        if not form.is_valid():
            return render(
                request,
                IMAGE_MODAL_TEMPLATE,
                {
                    "container": container,
                    "form": form,
                },
                status=422,
            )

        container = form.save()

        restart_marked = mark_container_restart_required(
            container_id=container.pk,
            reason="Container image changed",
        )

        response = render(
            request,
            CARD_WRAPPER_TEMPLATE,
            {"container": container},
        )

        response["HX-Trigger"] = json.dumps(
            {
                "modal-close": True,
                "kooplex-toast": {
                    "message": "Image updated.",
                    "level": "success",
                },
            }
        )

        broadcast_container_runtime_changed(
            container,
            reason="container.image.updated",
        )

        return response


class ContainerMountsModalView(
    LoginRequiredMixin, 
    MountSelectionMixin,
    TemplateView,
):
    template_name = MOUNTS_MODAL_TEMPLATE

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        container = get_object_or_404(
            Container.objects.filter(user=self.request.user),
            pk=self.kwargs["pk"],
        )

        current = get_current_container_mount_ids(container)

        context.update(
            {
                "container": container,
                "projects": self.get_projects(),
                "courses": self.get_courses(),
                "volumes": self.get_volumes(),
                "selected_project_ids": current["project_ids"],
                "selected_course_ids": current["course_ids"],
                "selected_volume_ids": current["volume_ids"],
            }
        )

        return context

    #FIXME
    def get_current_project_ids(self, container):
        return set(
            ProjectContainerBinding.objects
            .filter(container=container)
            .values_list("project_id", flat=True)
        )

    def get_current_course_ids(self, container):
        # Replace with your real binding model.
        return set()

    def get_current_volume_ids(self, container):
        # Replace with your real binding model.
        return set()


class ContainerMountsSaveView(
    LoginRequiredMixin, 
    MountSelectionMixin,
    View,
):
    def post(self, request, pk):
        container = get_object_or_404(
            Container.objects.filter(user=request.user),
            pk=pk,
        )

        projects = self.get_selected_projects()
        courses = self.get_selected_courses()
        volumes = self.get_selected_volumes()

        changes = self.apply_mounts(
            container=container,
            projects=projects,
            courses=courses,
            volumes=volumes,
        )

        response = render(
            request,
            CARD_WRAPPER_TEMPLATE,
            {"container": container},
        )

        message = mount_change_message(changes)
        response["HX-Trigger"] = json.dumps(
            {
                "modal-close": True,
                "kooplex-toast": {
                    "message": message,
                    "level": "success",
                },
            }
        )
        logger.debug(message)
        broadcast_container_runtime_changed(
            container,
            reason=(
                f"container.mounts.changed"
            ),
        )

        return response

    def apply_mounts(self, container, projects, courses, volumes):
        return apply_container_mounts(
            container=container,
            projects=projects,
            courses=courses,
            volumes=volumes,
        )


