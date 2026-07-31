from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View

from ..mixins import ContainerAccessMixin


class ContainerEditableWidgetMixin(ContainerAccessMixin):
    form_class = None
    display_template_name = None
    edit_template_name = None

    def get_form_kwargs(self, container):
        kwargs = {
            "instance": container,
        }

        if self.request.method == "POST":
            kwargs["data"] = self.request.POST

        return kwargs

    def get_form(self, container):
        if self.form_class is None:
            raise NotImplementedError("form_class must be defined")

        return self.form_class(
            **self.get_form_kwargs(container)
        )

    def get_display_context(self, container):
        return {
            "container": container,
        }

    def get_edit_context(self, container, form):
        return {
            "container": container,
            "form": form,
            "errors": form.errors,
        }

    def render_display(self, container):
        return render(
            self.request,
            self.display_template_name,
            self.get_display_context(container),
        )

    def render_edit(self, container, form):
        return render(
            self.request,
            self.edit_template_name,
            self.get_edit_context(container, form),
        )

    def can_edit(self, container):
        return True

    def after_save(self, container, form):
        """
        Hook for restart marking, live broadcasts, and toast messages.
        """
        return None


class ContainerWidgetDisplayView(
    LoginRequiredMixin,
    ContainerEditableWidgetMixin,
    View,
):
    def get(self, request, pk):
        container = self.get_container()
        return self.render_display(container)


class ContainerWidgetEditView(
    LoginRequiredMixin,
    ContainerEditableWidgetMixin,
    View,
):
    def get(self, request, pk):
        container = self.get_container()

        if not self.can_edit(container):
            return self.render_display(container)

        form = self.get_form(container)

        return self.render_edit(
            container=container,
            form=form,
        )


class ContainerWidgetUpdateView(
    LoginRequiredMixin,
    ContainerEditableWidgetMixin,
    View,
):
    def post(self, request, pk):
        container = self.get_container()

        if not self.can_edit(container):
            return self.render_display(container)

        form = self.get_form(container)

        if not form.is_valid():
            return self.render_edit(
                container=container,
                form=form,
            )

        changed_fields = list(form.changed_data)

        container = form.save()

        response = self.render_display(container)

        if changed_fields:
            self.after_save(
                container=container,
                form=form,
            )

            response = self.add_success_headers(
                response=response,
                container=container,
                form=form,
            )

        return response

    def add_success_headers(
        self,
        response,
        container,
        form,
    ):
        return response

