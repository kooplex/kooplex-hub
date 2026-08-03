import json
import logging

from django.contrib.auth import get_user_model
from django.template.response import TemplateResponse
from django.http import HttpResponse

from .base import ProjectEditorBaseView
from ...forms import ProjectMountsForm
from ...models import UserProjectBinding
from ...services.mounts import update_project_mounts


User = get_user_model()
logger = logging.getLogger(__name__)

MOUNTS_DISPLAY_TEMPLATE = "ui/editors/mounts_picker/summary.html"
MOUNTS_MODAL_TEMPLATE = "ui/editors/mounts_picker/modal.html"
MOUNTS_MODAL_CONTENT_TEMPLATE = "ui/editors/mounts_picker/modal_content.html"


class ProjectMountsBaseView(ProjectEditorBaseView):
    field_name = None
    permission_name = "can_change_mounts"
    editor_slug = "mounts"
    aria_label = "Manage project mounts"

    def get_form(self, *, data=None):
        project = self.get_project()

        initial_mount_ids = (
            project.volumebindings
            .values_list("volume_id", flat=True)
        )

        return ProjectMountsForm(
            data=data,
            actor=self.request.user,
            initial={
                "mounts": initial_mount_ids,
            },
            auto_id=(
                f"project-{project.pk}-mounts-%s"
            ),
        )

    def get_selected_mounts(
        self,
        *,
        form=None,
    ):
        if form is not None and form.is_bound:
            return form.get_selected_mounts()

        return [
            binding.volume
            for binding in (
                self.get_project()
                .volumebindings
                .select_related("volume")
            )
        ]

    def extend_editor_context(
        self,
        context,
        *,
        form=None,
    ):
        project = self.get_project()

        if form is None:
            selected_mounts = tuple(
                binding.volume
                for binding in (
                    project.volumebindings
                    .select_related("volume")
                )
            )

            available_mounts = ()
        else:
            available_mounts = tuple(
                form.fields["mounts"].queryset
            )

            if form.is_bound:
                selected_mounts = (
                    form.get_selected_mounts()
                )
            else:
                selected_mounts = tuple(
                    binding.volume
                    for binding in (
                        project.volumebindings
                        .select_related("volume")
                    )
                )

        selected_ids = {
            volume.pk
            for volume in selected_mounts
        }

        context.update({
            "selected_mounts": selected_mounts,
            "available_mounts": (
                available_mounts
            ),
            "items": tuple(
                {
                    "volume": volume,
                    "selected": (
                        volume.pk in selected_ids
                    ),
                }
                for volume in available_mounts
            ),
            "staged": False,
        })

        return context


class ProjectMountsDisplayView(
    ProjectMountsBaseView
):
    template_name = MOUNTS_DISPLAY_TEMPLATE

    def get_context_data(
        self,
        **kwargs,
    ):
        return {
            "editor": self.make_editor_context(),
        }


class ProjectMountsModalView(
    ProjectMountsBaseView,
):
    template_name = MOUNTS_MODAL_TEMPLATE

    def get_context_data(self, **kwargs):
        self.require_edit_permission()

        form = (
            kwargs.get("form")
            or self.get_form()
        )

        return {
            "editor": self.make_editor_context(form=form),
        }


class ProjectMountsUpdateView(
    ProjectMountsBaseView
):
    http_method_names = ["post"]

    def post(
        self,
        request,
        *args,
        **kwargs,
    ):
        self.require_edit_permission()

        form = self.get_form(
            data=request.POST,
        )

        if not form.is_valid():
            return TemplateResponse(
                request,
                MOUNTS_MODAL_CONTENT_TEMPLATE,
                {
                    "editor": (
                        self.make_editor_context(
                            form=form,
                        )
                    ),
                },
            )

        project = self.get_project()

        changes = update_project_mounts(
            project=project,
            actor=request.user,
            mounts=form.cleaned_data["mounts"],
        )

        if changes.changed:
            logger.info(
                "Project %s mounts changed by %s: "
                "%d added, %d removed",
                project.pk,
                request.user.pk,
                len(changes.added),
                len(changes.removed),
            )

        response = HttpResponse(status=204)
        response["HX-Trigger"] = json.dumps({
            "modal-close": True,
            "project-mounts-updated": {
                "project_id": project.pk,
            },
        })

        return response
