from django import forms
from django.utils.translation import gettext_lazy as _

from ..models import CGroup as Group


class MyDescription(forms.Textarea):
    def __init__(self, *args, **kwargs):
        super(MyDescription, self).__init__(*args, **kwargs)
        self.attrs['rows'] = 3
        self.attrs['cols'] = 30


class FormGroup(forms.ModelForm):
    description = forms.CharField(
            max_length = 100, required = True,
            help_text = _('It is always a good idea to have a hint of the group.'), 
            widget = MyDescription, 
        )

    class Meta:
        model = Group
        fields = [ 'name', 'description', 'course' ]
        labels = {
            'name': _('Group name'),
            'description': _('A short description'),
            'course': _('The course to define a new group'),
        }

    def __init__(self, *args, **kwargs):
        course = kwargs.pop('course', None)
        super(FormGroup, self).__init__(*args, **kwargs)
        if course is not None:
            self.fields["course"].choices = [(course.id, course),]
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


