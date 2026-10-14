import logging
import json

from django.shortcuts import redirect, get_object_or_404
from django.http import HttpResponse, HttpResponseForbidden
from django.template.response import TemplateResponse
from django.views.decorators.http import require_POST
from django.urls import reverse_lazy, reverse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views import generic
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.html import format_html

from hub.templatetags.extras import manual_link

from .models import Volume, UserVolumeBinding
from .forms import FormAttachment
from .forms.edit import VolumeDescriptionForm, VolumeScopeForm
from .services.access import resolve_volume_access
from .services.lifecycle import delete_attachment, VolumeLifecycleError


logger = logging.getLogger(__name__)

class VolumeListView(LoginRequiredMixin, generic.ListView):
    template_name = 'volume/list.html'
    context_object_name = 'volumes'
    model = Volume

    def get_context_data(self, **kwargs):
        l = manual_link(item = "volume")
        context = super().get_context_data(**kwargs)
        context['menu_storage'] = True
        context['url_new_attachment'] = reverse('volume:new_attachment')
        context['page_title'] = 'Storage'
        context['documentation_url'] = 'https://xwiki.vo.elte.hu/en/kooplex-manual/storages'
        context['empty_title'] = 'No volumes available'
        context['empty_body'] = format_html(f'You do no have access to the volumes yet. Ask volume owners or volume administrators for collaboration. {l}')
        context["cards"] = [volume_card_context(v, self.request.user) for v in context["volumes"]]
        return context

    def get_queryset(self):
        return (Volume.objects.visible_to(self.request.user)
                .prefetch_related("containerbindings__container__user")
                .order_by("folder", "pk"))



class NewAttachmentView(LoginRequiredMixin, generic.FormView):
    template_name = 'volume/new.html'
    form_class = FormAttachment
    success_url = reverse_lazy('volume:list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['menu_storage'] = True
        return context

    def form_valid(self, form):
        logger.info(form.cleaned_data)
        user = self.request.user
        v = Volume.objects.create(**form.cleaned_data)
        UserVolumeBinding.objects.create(volume = v, user = user, role = UserVolumeBinding.Role.OWNER) 
        messages.info(self.request, f'Attachment {v.folder} is created')
        return super().form_valid(form)


# Volume card presentation, with permissions computed on the server.
SCOPE_ICONS = {
    Volume.Scope.PRIVATE: "bi-lock",
    Volume.Scope.INTERNAL: "bi-people",
    Volume.Scope.PUBLIC: "bi-globe",
    Volume.Scope.ATTACHMENT: "bi-paperclip",
}
STATE_ICONS = {
    Volume.ProvisioningState.READY: "bi-check-circle text-success",
    Volume.ProvisioningState.PREPARING: "bi-hourglass-split text-warning",
    Volume.ProvisioningState.DELETING: "bi-trash text-secondary",
    Volume.ProvisioningState.FAILED: "bi-exclamation-circle text-danger",
}


def volume_card_context(volume, user):
    access = resolve_volume_access(volume=volume, user=user)
    can_manage = access.manageable
    can_delete = (volume.scope == Volume.Scope.ATTACHMENT
                  and Volume.objects.owned_by(user).filter(pk=volume.pk).exists()
                  and volume.provisioning_state != Volume.ProvisioningState.DELETING)
    referencing_containers = sorted(
        (binding.container for binding in volume.containerbindings.all()),
        key=lambda container: (container.user.username, container.name, container.pk),
    )
    base = {"pk": volume.pk}
    def editor(field, *, form=None):
        prefix = f"volume:{field}-"
        result = {
            "dom_id": f"volume-{volume.pk}-{field}",
            "value": getattr(volume, field),
            "field": form[field] if form else None,
            "form": form,
            "can_edit": can_manage and (field != "scope" or volume.scope != Volume.Scope.ATTACHMENT),
            "aria_label": f"Change volume {field}",
            "edit_url": reverse(prefix + "edit", kwargs=base),
            "display_url": reverse(prefix + "display", kwargs=base),
            "update_url": reverse(prefix + "update", kwargs=base),
        }
        if field == "description":
            result["edit_hint"] = "Click to edit"
        else:
            result.update({
                "icon": SCOPE_ICONS[volume.scope],
                "display_value": volume.scope.title(),
                "description": volume.get_scope_display(),
                "choices": [{"value": val, "label": val.title(), "description": label,
                             "icon": SCOPE_ICONS[val]}
                            for val, label in Volume.Scope.choices if val != Volume.Scope.ATTACHMENT],
            })
        return result

    return {
        "volume": volume,
        "description_editor": editor("description"),
        "scope_editor": editor("scope"),
        "state_icon": STATE_ICONS.get(volume.provisioning_state, "bi-question-circle"),
        "can_delete": can_delete,
        "referencing_containers": referencing_containers,
        "delete_url": reverse("volume:destroy", kwargs=base),
    }


class VolumeCardView(LoginRequiredMixin, generic.View):
    def get(self, request, pk):
        volume = get_object_or_404(Volume.objects.visible_to(request.user), pk=pk)
        return TemplateResponse(request, "volume/card.html", {"card": volume_card_context(volume, request.user)})


class VolumeEditorView(LoginRequiredMixin, generic.View):
    field = None  # bound by URL wrapper
    action = None

    def dispatch(self, request, pk, field, action, *args, **kwargs):
        if field not in ("description", "scope") or action not in ("display", "edit", "update"):
            return HttpResponse(status=404)
        if action == "update" and request.method != "POST":
            return HttpResponse(status=405)
        if action != "update" and request.method != "GET":
            return HttpResponse(status=405)
        volume = get_object_or_404(Volume.objects.visible_to(request.user), pk=pk)
        access = resolve_volume_access(volume=volume, user=request.user)
        permitted = access.manageable and (field != "scope" or volume.scope != Volume.Scope.ATTACHMENT)
        if action != "display" and not permitted:
            return HttpResponseForbidden("You cannot edit this volume.")
        form_class = VolumeDescriptionForm if field == "description" else VolumeScopeForm
        form = form_class(request.POST if action == "update" else None, instance=volume)
        if action == "update" and form.is_valid():
            form.save()
            action = "display"
        card = volume_card_context(volume, request.user)
        editor = card[field + "_editor"]
        if action != "display":
            editor["field"] = form[field]
            editor["form"] = form
        return TemplateResponse(request, f"ui/editors/{field}/{'edit' if action != 'display' else 'display'}.html", {"editor": editor})


@login_required
@require_POST
def destroy(request, pk):
    attachment = get_object_or_404(Volume.objects.visible_to(request.user), pk=pk)
    try:
        delete_attachment(attachment=attachment, actor=request.user)
    except VolumeLifecycleError as exc:
        messages.error(request, str(exc))
    else:
        messages.info(request, f"Deletion requested for {attachment.folder}.")
    return redirect("volume:list")
