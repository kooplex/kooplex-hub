from .widgets import CourseWidgetForm

class CoursePreferredImageForm(CourseWidgetForm):
    class Meta(CourseWidgetForm.Meta):
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

