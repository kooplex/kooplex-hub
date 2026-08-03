from django import forms

from volume.models import Volume


class ProjectMountsForm(
    forms.Form,
):
    mounts = forms.ModelMultipleChoiceField(
        queryset=Volume.objects.none(),
        required=False,
        widget=forms.MultipleHiddenInput,
    )

    def __init__(
        self, 
        *args, 
        actor, 
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        self.actor = actor

        self.fields["mounts"].queryset = Volume.objects.visible_to(actor)

    def get_selected_mounts(self):
        if not self.is_bound:
            return ()

        selected_ids = self.data.getlist(
            self.add_prefix("mounts")
        )

        if not selected_ids:
            return ()

        volumes_by_id = {
            str(volume.pk): volume
            for volume in (
                self.fields["mounts"]
                .queryset
                .filter(pk__in=selected_ids)
            )
        }

        return tuple(
            volumes_by_id[selected_id]
            for selected_id in selected_ids
            if selected_id in volumes_by_id
        )

