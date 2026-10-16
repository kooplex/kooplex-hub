from django.shortcuts import get_object_or_404

from ..services.runtime_presenter import ContainerRuntimePresenter
from ..models import Container
from project.models import Project
from education.models import Course
from volume.models import Volume
from volume.conf import VOLUME_SETTINGS
from project.services.project_presenter import ProjectPresenter
from project.conf import PROJECT_SETTINGS
from education.conf import EDUCATION_SETTINGS


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
    def present_projects(self, queryset):
        projects = list(queryset)
        for project in projects:
            project.mount_presenter = ProjectPresenter(
                project=project, user=self.request.user,
            )
            members = project.mount_presenter.mount_members
            project.mount_members = members
            project.mount_team_tooltip = "\n".join(
                f"{member['user'].get_full_name() or member['user'].username} ({member['role_label']})"
                for member in members
            )
            mounts = PROJECT_SETTINGS.mounts
            project.mount_targets = (
                ("Project", mounts.project.mountpoint.format(project=project)),
                ("Report preparation", mounts.report_prepare.mountpoint.format(project=project)),
            )
            project.mount_tooltip = "Configured mount points:\n" + "\n".join(
                f"{label}: {target}" for label, target in project.mount_targets
            )
        return projects

    def present_courses(self, queryset):
        courses = list(queryset)
        mounts = EDUCATION_SETTINGS.mounts
        for course in courses:
            membership = next(
                (binding for binding in course.userbindings.all()
                 if binding.user_id == self.request.user.pk),
                None,
            )
            course.mount_role = (
                "Teacher" if membership.is_teacher else "Student"
            ) if membership is not None else "—"
            course.mount_role_icon = (
                EDUCATION_SETTINGS.presentation.role_icons[
                    "teacher" if membership.is_teacher else "student"
                ]
                if membership is not None else None
            )
            course.mount_targets = (
                ("Workdir", mounts.workdir.mountpoint.format(course=course)),
                ("Public", mounts.public.mountpoint.format(course=course)),
                ("Assignment preparation", mounts.prepare.mountpoint.format(course=course)),
                ("Assignment workdir", mounts.assignment.mountpoint.format(course=course)),
            )
            course.mount_tooltip = "Configured mount points:\n" + "\n".join(
                f"{label}: {target}" for label, target in course.mount_targets
            )
        return courses

    def present_volumes(self, queryset):
        volumes = list(queryset)
        for volume in volumes:
            volume.mount_target = VOLUME_SETTINGS.mountpoint.format(volume=volume)
            volume.mount_tooltip = (
                "Configured mount point:\n"
                f"{volume.mount_target}"
            )
        return volumes

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
        return self.present_projects(
            Project.objects
            .attachable_by(self.request.user)
            .prefetch_related("userbindings__user")
            .order_by("name")
        )

    def get_courses(self):
        return self.present_courses(
            Course.objects
            .attachable_by(self.request.user)
            .prefetch_related("userbindings__user")
            .order_by("name")
        )

    def get_volumes(self):
        return self.present_volumes(
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
