from django import forms
from django.utils.translation import gettext_lazy as _

from container.models import Image
from ..models import Course

from kooplexhub.lib import my_slug_validator, my_end_validator


class MyDescription(forms.Textarea):
    def __init__(self, *args, **kwargs):
        super(MyDescription, self).__init__(*args, **kwargs)
        self.attrs['rows'] = 3
        self.attrs['cols'] = 30


class FormCourse(forms.Form):
    name = forms.CharField(
            label = _("Course name"),
            help_text = _('A short name of the course, but it has to be unique among course names.'), 
            max_length = 100, required = True,
#            validators = [
#                    my_slug_validator('Enter a valid project name containing only letters, numbers, underscores or hyphens.'),
#                    my_end_validator('Enter a valid project name ending with a letter or number.'),
#                ],
            )
    description = forms.CharField(
            max_length = 100, required = True,
            help_text = _('It is always a good idea to have an abstract of your project.'), 
            widget = MyDescription, 
            )
    image = forms.ModelChoiceField(queryset = Image.objects.filter(imagetype = Image.TP_PROJECT), help_text = _('Select an image if you prefer for the course'), required = True, empty_label = 'Select image...')
    #FIXME: other_teachers_can_delete_my_assignments boolean be added in models too

    def __init__(self, *args, **kwargs):
        super(FormCourse, self).__init__(*args, **kwargs)
        try:
            self.fields['image'].initial = args[0]['image'].id
        except:
            pass

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

