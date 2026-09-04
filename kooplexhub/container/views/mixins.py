from django.shortcuts import get_object_or_404

from ..services.runtime_presenter import ContainerRuntimePresenter
from ..models import Container
from project.models import Project
from education.models import Course
from volume.models import Volume


class ContainerAccessMixin:
    pk_url_kwarg = "pk"

    def get_container_queryset(self):
        return Container.objects.filter(user=self.request.user)

    def get_container(self, pk=None):
        pk = pk or self.kwargs.get(self.pk_url_kwarg)

        return get_object_or_404(
            self.get_container_queryset(),
            pk=pk,
        )


class MountSelectionMixin:
    def _ids_from_request(self, name):
        return {
            int(value)
            for value in self.request.GET.getlist(name)
            if str(value).isdigit()
        }

    def _ids_from_post(self, name):
        return {
            int(value)
            for value in self.request.POST.getlist(name)
            if str(value).isdigit()
        }

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

    def get_selected_projects(self):
        return (
            Project.objects
            .attachable_by(self.request.user)
            .filter(pk__in=self._ids_from_post("project_ids"))
            .prefetch_related("userbindings__user")
            .order_by("name")
        )

    def get_selected_courses(self):
        return (
            Course.objects
            .attachable_by(self.request.user)
            .filter(pk__in=self._ids_from_post("course_ids"))
            .prefetch_related("userbindings__user")
            .order_by("name")
        )

    def get_selected_volumes(self):
        return (
            Volume.objects
            .attachable_by(self.request.user)
            .filter(pk__in=self._ids_from_post("volume_ids"))
            .prefetch_related("userbindings__user")
            .order_by("folder")
        )


class ContainerRuntimePartialMixin(ContainerAccessMixin):
    def get_context_data_for_container(self, container):
        return {
            "container": container,
            "runtime": ContainerRuntimePresenter(container),
        }
