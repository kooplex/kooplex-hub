from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.views.generic import TemplateView
from django.views import View
from django.shortcuts import render
from django.urls import reverse

from ..mixins import ContainerAccessMixin
from ...services.runtime_presenter import ContainerRuntimePresenter


class ContainerEditorBaseView(
    LoginRequiredMixin,
    ContainerAccessMixin,
    TemplateView,
):
    pk_url_kwarg = "container_id"

    container = None
    presenter = None

    field_name = None
    permission_name = None
    editor_slug = None
    aria_label = None

    def get_container(self, pk=None):
        if self.container is None:
            self.container = super().get_container(pk=pk)
        return self.container

    def get_presenter(self):
        if self.presenter is None:
            self.presenter = ContainerRuntimePresenter(
                container=self.get_container(),
            )
        return self.presenter

    def require_edit_permission(self):
        presenter = self.get_presenter()

        if not getattr(presenter, self.permission_name):
            raise PermissionDenied

        return presenter

    def get_editor_urls(self):
        container = self.get_container()
        kwargs = {"pk": container.pk}

        return {
            "edit_url": reverse(
                f"container:{self.editor_slug}_edit",
                kwargs=kwargs,
            ),
            "display_url": reverse(
                f"container:{self.editor_slug}_display",
                kwargs=kwargs,
            ),
            "update_url": reverse(
                f"container:{self.editor_slug}_update",
                kwargs=kwargs,
            ),
        }

    def get_editor_value(self):
        if self.field_name is None:
            return None

        return getattr(
            self.get_container(),
            self.field_name,
        )

    def get_editor_field(self, *, form=None):
        if form is None or self.field_name is None:
            return None

        return form[self.field_name]

    def extend_editor_context(
        self,
        context,
        *,
        form=None,
    ):
        return context

    def make_editor_context(self, *, form=None):
        container = self.get_container()

        context = {
            "dom_id": (
                f"container-{container.pk}-"
                f"{self.editor_slug}"
            ),
            "value": self.get_editor_value(),
            "field": self.get_editor_field(
                form=form,
            ),
            "form": form,
            "can_edit": getattr(
                self.get_presenter(),
                self.permission_name,
            ),
            "aria_label": self.aria_label,
            **self.get_editor_urls(),
        }

        return self.extend_editor_context(
            context,
            form=form,
        )

    def refresh_editor_state(self, container):
        self.container = container
        self.presenter = None


class ContainerEditableWidgetMixin(ContainerAccessMixin):
    #FIXME: this class may go after migrating functionalities to ContainerEditorBaseView
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

