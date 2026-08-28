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
from ..services.lifecycle import (
    ContainerLifecycleError,
    create_container,
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
    template_name = (
        "container/partials/create_modal.html"
    )

    def post(self, request):
        form = ContainerCreateForm(
            request.POST,
            user=request.user,
        )

        project_ids = self._ids_from_post(
            "project_ids"
        )
        course_ids = self._ids_from_post(
            "course_ids"
        )
        volume_ids = self._ids_from_post(
            "volume_ids"
        )

        if not form.is_valid():
            return self.render_invalid(
                form=form,
                project_ids=project_ids,
                course_ids=course_ids,
                volume_ids=volume_ids,
            )

        try:
            container = create_container(
                user=request.user,
                name=form.cleaned_data[
                    "name"
                ],
                image=form.cleaned_data[
                    "image"
                ],
                project_ids=project_ids,
                course_ids=course_ids,
                volume_ids=volume_ids,
            )

        except ContainerLifecycleError as error:
            form.add_error(
                None,
                str(error),
            )

            return self.render_invalid(
                form=form,
                project_ids=project_ids,
                course_ids=course_ids,
                volume_ids=volume_ids,
            )

        response = HttpResponse(
            status=204
        )

        response["HX-Trigger"] = (
            json.dumps({
                "container-list-refresh": True,
                "modal-close": True,
                "kooplex-toast": {
                    "message": (
                        f"Environment "
                        f"'{container.name}' "
                        "was created."
                    ),
                    "level": "success",
                },
            })
        )

        return response

    def _ids_from_post(self, name):
        return [
            int(value)
            for value in self.request.POST.getlist(name)
            if str(value).isdigit()
        ]

    def render_invalid(
        self,
        *,
        form,
        project_ids,
        course_ids,
        volume_ids,
    ):
        return render(
            self.request,
            self.template_name,
            {
                "form": form,
                "selected_image": (
                    form.cleaned_data.get(
                        "image"
                    )
                    if hasattr(
                        form,
                        "cleaned_data",
                    )
                    else None
                ),
                "selected_projects": (
                    self.get_projects(
                        project_ids
                    )
                ),
                "selected_courses": (
                    self.get_courses(
                        course_ids
                    )
                ),
                "selected_volumes": (
                    self.get_volumes(
                        volume_ids
                    )
                ),
            },
            status=422,
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


