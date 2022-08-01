from django import forms
from django.utils.translation import gettext_lazy as _

from ..models import CourseGroup


class FormGroup(forms.ModelForm):
    prefix = 'group'
    name = forms.CharField(label = _('Group name'), required = False)
    description = forms.CharField(
            max_length = 100, required = False, 
            help_text = _('It is always a good idea to have a hint of the group.'), 
            widget = forms.Textarea(attrs = {'rows': 3 }),
        )

    class Meta:
        model = CourseGroup
        fields = [ 'name', 'description' ]
        labels = {
            'name': _('Group name'),
            'description': _('A short description'),
            'course': _('The course to define a new group'),
        }

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data['name'] :
            raise forms.ValidationError(_(f'Group name is missing'), code = 'invalid specification')
        if not cleaned_data['description']:
            raise forms.ValidationError(_(f'Group description is missing'), code = 'invalid specification')
        return cleaned_data

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            help_text = self.fields[field].help_text
            self.fields[field].help_text = None
            self.fields[field].widget.attrs["class"] = "form-control"
            self.fields[field].widget.attrs["style"] = "width: 100%"
            if help_text != '':
                extra = {
                    'data-toggle': 'tooltip', 
                    'title': help_text,
                    'data-placement': 'bottom',
                }
                self.fields[field].widget.attrs.update(extra)


