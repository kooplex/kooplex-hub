from django import forms
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html

from container.models import Image
from ..models import Course

from kooplexhub.lib import my_slug_validator, my_end_validator

class FormCourse(forms.Form):
    prefix = 'course'
    name = forms.CharField(
        label = _("Course name"),
        help_text = _('A short name of the course, but it has to be unique among course names.'), 
        max_length = 100, required = True,
    )
    description = forms.CharField(
        max_length = 100, required = True,
        help_text = _('It is always a good idea to have a description of your course.'), 
        widget = forms.Textarea(attrs = {'rows': 3 }),
    )
    image = forms.ModelChoiceField(
        queryset = Image.objects.filter(imagetype = Image.TP_PROJECT, present = True), 
        help_text = _('Select an image you recommend your students the most to work with during the semester in the given course.'), required = True, empty_label = 'Select image...'
    )

    class Meta:
        model = Course
        fields = [ 'name', 'description', 'image' ]

    def descriptions(self):
        hidden = lambda i: f"""<input type="hidden" id="image-description-{i.id}" value="{i.description}">"""
        return format_html("".join(list(map(hidden, self.fields['image'].queryset))))

    def __init__(self, *args, **kwargs):
        if hasattr(self, 'prefix'):
            d = {}
            for l in [ 'name', 'description', 'image' ]:
                if l in args[0]:
                    v = args[0].pop(l)
                    d[f'{self.prefix}-{l}'] = v
            args[0].update(d)
        super(FormCourse, self).__init__(*args, **kwargs)

        for field in self.fields:
            help_text = self.fields[field].help_text
            self.fields[field].help_text = None
            self.fields[field].widget.attrs["class"] = "form-control"
            if help_text != '':
                extra = {
                    'data-toggle': 'tooltip', 
                    'title': help_text,
                    'data-placement': 'bottom',
                }
                self.fields[field].widget.attrs.update(extra)

