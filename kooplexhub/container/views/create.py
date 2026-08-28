import logging
import json

from django.views.generic import (
    View,
    TemplateView,
    DetailView,
)
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import (
    render,
    HttpResponse,
)

from ..models import Image
from ..forms import  ContainerCreateForm
from ..services.image_catalog import ImageCatalogService
from ..services.mounts import (
    apply_container_mounts, 
    mount_change_message,
)
from ..services.live import (
    broadcast_container_runtime_changed,
)
from project.models import Project
from education.models import Course
from volume.models import Volume


logger = logging.getLogger(__name__)


class ContainerCreateModalView(
    LoginRequiredMixin, 
    TemplateView,
):
    template_name = "container/partials/create_modal.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = ContainerCreateForm(user=self.request.user)
        context["selected_image"] = None
        return context


class ContainerCreateView(
    LoginRequiredMixin, 
    View,
):
    template_name = "container/partials/create_modal.html"

    def post(self, request):
        form = ContainerCreateForm(
            request.POST,
            user=request.user,
        )

        selected_image = self.get_selected_image()
        selected_projects = self.get_selected_projects()
        selected_courses = self.get_selected_courses()
        selected_volumes = self.get_selected_volumes()

        if not form.is_valid():
            return render(
                request,
                self.template_name,
                {
                    "form": form,
                    "selected_image": selected_image,
                    "selected_projects": selected_projects,
                    "selected_courses": selected_courses,
                    "selected_volumes": selected_volumes,
                },
            )

        container = form.save(commit=False)
        container.user = request.user

        if selected_image is not None:
            container.image = selected_image

        container.save()

        changes = self.apply_mounts(
            container=container,
            projects=selected_projects,
            courses=selected_courses,
            volumes=selected_volumes,
        )

        response = HttpResponse(status=204)
        mount_message = mount_change_message(changes)
        logger.debug(mount_message)
        response["HX-Trigger"] = json.dumps(
            {
                "container-list-refresh": True,
                "modal-close": True,
                "kooplex-toast": {
                    "message": f"Environment '{container.name}' was created.",
                    "level": "success",
                },
            }
        )
        broadcast_container_runtime_changed(
            container,
        )
        return response

    def get_selected_image(self):
        image_id = self.request.POST.get("image")

        if not image_id:
            return None

        return (
            ImageCatalogService.available_for_user(user=self.request.user)
            .filter(pk=image_id)
            .first()
        )

    def get_selected_projects(self):
        ids = self._ids_from_post("project_ids")

        return (
            Project.objects
            .attachable_by(self.request.user)
            .filter(pk__in=ids)
            .order_by("name")
        )

    def get_selected_courses(self):
        ids = self._ids_from_post("course_ids")

        return (
            Course.objects
            .attachable_by(self.request.user)
            .filter(pk__in=ids)
            .order_by("name")
        )

    def get_selected_volumes(self):
        ids = self._ids_from_post("volume_ids")

        return (
            Volume.objects
            .attachable_by(self.request.user)
            .filter(pk__in=ids)
            .order_by("folder")
        )

    def _ids_from_post(self, name):
        return [
            int(value)
            for value in self.request.POST.getlist(name)
            if str(value).isdigit()
        ]

    def apply_mounts(self, container, projects, courses, volumes):
        return apply_container_mounts(
            container=container,
            projects=projects,
            courses=courses,
            volumes=volumes,
        )


class ContainerCreateImagePickerView(
    LoginRequiredMixin, 
    TemplateView,
):
    template_name = "container/partials/create_image_picker.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        images = ImageCatalogService.available_for_user(user=self.request.user)

        selected_id = self.request.GET.get("image")
        selected_image = None

        if selected_id:
            selected_image = images.filter(id=selected_id).first()

        if selected_image is None:
            selected_image = images.first()

        context["images"] = images
        context["selected_image"] = selected_image
        return context


class ContainerCreateImageSelectedView(
    LoginRequiredMixin, 
    DetailView,
):
    model = Image
    template_name = "container/partials/create_image_selected.html"
    context_object_name = "image"

    def get_queryset(self):
        return ImageCatalogService.available_for_user(user=self.request.user)


class ContainerCreateMountsPickerView(
    LoginRequiredMixin, 
    TemplateView
):
    template_name = "container/partials/create_mounts_picker.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        selected_project_ids = self._ids_from_request("project_ids")
        selected_course_ids = self._ids_from_request("course_ids")
        selected_volume_ids = self._ids_from_request("volume_ids")

        context.update({
            "projects": self.get_projects(),
            "courses": self.get_courses(),
            "volumes": self.get_volumes(),
            "selected_project_ids": selected_project_ids,
            "selected_course_ids": selected_course_ids,
            "selected_volume_ids": selected_volume_ids,
        })

        return context

    def _ids_from_request(self, name):
        values = self.request.GET.getlist(name)
        return {int(v) for v in values if str(v).isdigit()}

    def get_projects(self):
        return (
            Project.objects
            .attachable_by(self.request.user)
            .prefetch_related("userbindings__user")
            .order_by("name")
        )

    def get_courses(self):
        return (
            Course.objects
            .attachable_by(self.request.user)
            .prefetch_related("userbindings__user")
            .order_by("name")
        )


    def get_volumes(self):
        return (
            Volume.objects
            .attachable_by(self.request.user)
            .prefetch_related("userbindings__user")
            .order_by("folder")
        )


class ContainerCreateMountsSelectedView(
    LoginRequiredMixin, 
    TemplateView,
):
    template_name = "container/partials/create_mounts_selected.html"

    def post(self, request, *args, **kwargs):
        selected_project_ids = self._ids_from_post("project_ids")
        selected_course_ids = self._ids_from_post("course_ids")
        selected_volume_ids = self._ids_from_post("volume_ids")

        context = {
            "selected_projects": self.get_projects(selected_project_ids),
            "selected_courses": self.get_courses(selected_course_ids),
            "selected_volumes": self.get_volumes(selected_volume_ids),
        }

        return render(request, self.template_name, context)

    def _ids_from_post(self, name):
        values = self.request.POST.getlist(name)
        return [int(v) for v in values if str(v).isdigit()]

    def get_projects(self, ids):
        return (
            Project.objects
            .attachable_by(self.request.user)
            .filter(id__in=ids)
            .prefetch_related("userbindings__user")
            .order_by("name")
        )

    def get_courses(self, ids):
        return (
            Course.objects
            .attachable_by(self.request.user)
            .filter(id__in=ids)
            .prefetch_related("userbindings__user")
            .order_by("name")
        )


    def get_volumes(self, ids):
        return (
            Volume.objects
            .attachable_by(self.request.user)
            .filter(id__in=ids)
            .prefetch_related("userbindings__user")
            .order_by("folder")
        )


class ContainerCreatePickerEmptyView(
    LoginRequiredMixin,
    TemplateView,
):
    template_name = "container/partials/create_picker_empty.html"


