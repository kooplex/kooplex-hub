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

from ..models import Project
from .mixins import ProjectMemberAccessMixin
from container.views.mixins import MountSelectionMixin
from container.services.image_catalog import ImageCatalogService
from container.models import Container
#from ..services.live import broadcast_container_live_event
from ..services.mounts import (
#    apply_container_mounts, 
#    mount_change_message,
    get_current_mount_ids,
)


logger = logging.getLogger(__name__)


class ProjectImageModalView(
    LoginRequiredMixin, 
    TemplateView,
):
    template_name = "project/partials/image/modal.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        project = get_object_or_404(
            Project.objects.filter(userbindings__user=self.request.user),
            pk=self.kwargs["pk"],
        )

        images = ImageCatalogService.available_for_user(user=self.request.user)
        selected_image = project.preferred_image or images.first()

        context.update(
            {
                "project": project,
                "images": images,
                "selected_image": selected_image,
            }
        )

        return context


class ProjectImagePickerView(
    LoginRequiredMixin, 
    TemplateView,
):
    template_name = "project/partials/image/picker.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        project = get_object_or_404(
            Project.objects.filter(userbindings__user=self.request.user),
            pk=self.kwargs["pk"],
        )

        images = ImageCatalogService.available_for_user(user=self.request.user)

        selected_image = None
        image_id = self.request.GET.get("image")

        if image_id:
            selected_image = images.filter(pk=image_id).first()

        if selected_image is None:
            selected_image = project.preferred_image or images.first()

        context.update(
            {
                "project": project,
                "images": images,
                "selected_image": selected_image,
            }
        )

        return context


class ProjectImageSaveView(
    LoginRequiredMixin, 
    View,
):
    def post(self, request, pk):
        project = get_object_or_404(
            Project.objects.filter(userbindings__user=request.user),
            pk=pk,
        )

        image = get_object_or_404(
            ImageCatalogService.available_for_user(user=request.user),
            pk=request.POST.get("image"),
        )

        project.preferred_image = image
        project.save(update_fields=["preferred_image"])

        response = render(
            request,
            "project/partials/card_wrapper.html",
            {"project": project},
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
#        broadcast_container_live_event(
#            user=request.user,
#            keys=[
#                f"container:{container.pk}",
#                f"container-list:user:{request.user.pk}",
#            ],
#            payload={
#                "event": "object.changed",
#                "model": "container",
#                "id": container.pk,
#            },
#        )
        return response


class ProjectMountsModalView(
    LoginRequiredMixin, 
    MountSelectionMixin,
    TemplateView,
):
    template_name = "project/partials/mounts/modal.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        project = get_object_or_404(
            Project.objects.filter(userbindings__user=self.request.user),
            pk=self.kwargs["pk"],
        )

        current = get_current_mount_ids(project)

        context.update(
            {
                "project": project,
                "volumes": self.get_volumes(),
                "selected_volume_ids": current,
            }
        )

        return context


class ProjectMountsSaveView(
    LoginRequiredMixin, 
    MountSelectionMixin,
    View,
):
    def post(self, request, pk):
        project = get_object_or_404(
            Project.objects.filter(userbindings__user=request.user),
            pk=pk,
        )

        volumes = self.get_selected_volumes()

        changes = self.apply_mounts(
            project=project,
            volumes=volumes,
        )

        response = render(
            request,
            "project/partials/card_wrapper.html",
            {"project": project},
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
#        broadcast_container_live_event(
#            user=request.user,
#            keys=[
#                f"container:{container.pk}",
#                f"container-list:user:{request.user.pk}",
#            ],
#            payload={
#                "event": "object.changed",
#                "model": "container",
#                "id": container.pk,
#            },
#        )

        return response

    def apply_mounts(self, project, volumes):
        return "FIXME"
#        return apply_container_mounts(
#            container=container,
#            projects=projects,
#            courses=courses,
#            volumes=volumes,
#        )
#
#


class ProjectDeleteView(
    LoginRequiredMixin,
    ProjectMemberAccessMixin,
    View,
):
    def post(self, request, pk):
        project = self.get_project()

        project_id = project.pk
        project_name = project.name
        user_id = request.user.pk

        upb = project.userbindings.filter(user = request.user).first()
        if not upb:
            return redirect('project:list')
        if upb.role == upb.Role.CREATOR:
            project.delete()
            logger.debug("Deleting project %s", project)
            message = f"Project \"{project_name}\" was deleted."
        else:
            upb.delete()
            logger.debug("Leaving project %s", project)
            message = f"You left project \"{project_name}\"."

#        broadcast_container_live_event(
#            user=request.user,
#            keys=[
#                f"project-list:user:{user_id}",
#            ],
#            payload={
#                "event": "object.deleted",
#                "model": "project",
#                "id": project_id,
#            },
#        )
#
#        if request.headers.get("HX-Request") == "true":
#            response = HttpResponse(status=204)
#            response["HX-Trigger"] = (
#                '{"project-list-refresh": true, '
#                '"kooplex-toast": {'
#                f'"message": "{message}", '
#                '"level": "success"}}'
#            )
#            return response
#
        return redirect("project:list")
