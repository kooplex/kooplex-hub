from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.views import View

from ...forms.widgets import ContainerNameForm
from ..mixins import ContainerAccessMixin


class ContainerNameDisplayView(
    LoginRequiredMixin,
    ContainerAccessMixin,
    View,
):
    template_name = "ui/widgets/editable_text/display.html"

    def get(self, request, pk):
        container = self.get_container()

        return render(
            request,
            self.template_name,
            {
                "dom_id": container.name_dom_id,
                "value": container.name,
                "edit_url": container.name_edit_url,
            },
        )


class ContainerNameEditView(
    LoginRequiredMixin,
    ContainerAccessMixin,
    View,
):
    template_name = "ui/widgets/editable_text/form.html"

    def get(self, request, pk):
        container = self.get_container()

        return render(
            request,
            self.template_name,
            {
                "dom_id": container.name_dom_id,
                "field_name": "name",
                "value": container.name,
                "update_url": container.name_update_url,
                "cancel_url": container.name_display_url,
            },
        )


class ContainerNameUpdateView(
    LoginRequiredMixin,
    ContainerAccessMixin,
    View,
):
    display_template_name = "ui/widgets/editable_text/display.html"
    form_template_name = "ui/widgets/editable_text/form.html"

    def post(self, request, pk):
        container = self.get_container()

        form = ContainerNameForm(
            request.POST,
            instance=container,
        )

        if not form.is_valid():
            return render(
                request,
                self.form_template_name,
                {
                    "dom_id": container.name_dom_id,
                    "field_name": "name",
                    "value": request.POST.get("name", container.name),
                    "update_url": container.name_update_url,
                    "cancel_url": container.name_display_url,
                    "errors": form.errors.get("name"),
                },
                status=422,
            )

        container = form.save()

        return render(
            request,
            self.display_template_name,
            {
                "dom_id": container.name_dom_id,
                "value": container.name,
                "edit_url": container.name_edit_url,
            },
        )
