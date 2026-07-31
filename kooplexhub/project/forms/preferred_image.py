from .widgets import ProjectWidgetForm

class ProjectPreferredImageForm(ProjectWidgetForm):
    class Meta(ProjectWidgetForm.Meta):
        fields = ["preferred_image"]

    def __init__(
        self,
        *args,
        available_images,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        self.fields["preferred_image"].queryset = available_images
        self.fields["preferred_image"].required = True

