from django import forms
from django.utils.translation import gettext_lazy as _

from ..models import Assignment


class MyDescription(forms.Textarea):
    def __init__(self, *args, **kwargs):
        super(MyDescription, self).__init__(*args, **kwargs)
        self.attrs['rows'] = 3
        self.attrs['cols'] = 30


class FormAssignment(forms.ModelForm):
    folder = forms.ChoiceField(
            help_text = _('A snapshot will be created of all files in the selected folder, and students will receive a copy of this snapshot.'),
        )
    description = forms.CharField(
            max_length = 100, required = True,
            help_text = _('It is always a good idea to have an abstract of your assignment.'), 
            widget = MyDescription, 
        )
    can_studentsubmit = forms.BooleanField(
            label=_('Student can submit earlier'), 
            required = False, 
            help_text=_('Student can submit earlier even when you set an expiry date.')
        )
    valid_from = forms.DateTimeField(
            input_formats = ["%m/%d/%y %H:%M"], 
            widget = forms.DateTimeInput(attrs = { "class": "datetimepicker span2" }), 
            required = False, 
            help_text = _('If unspecified the assignment folder is populated to students right away.'),
        )
    expires_at = forms.DateTimeField(
            input_formats = ["%m/%d/%y %H:%M"], 
            widget = forms.DateTimeInput(attrs = { "class": "datetimepicker span2" }), 
            required = False,
            help_text = _('If unspecified either you or students need to take care of collecting or submitting assignments respectively.'),
        )


    class Meta:
        model = Assignment
        fields = [ 'name', 'folder', 'description', 'can_studentsubmit', 'remove_collected', 'valid_from', 'expires_at', 'max_number_of_files', 'max_size' ]
        labels = {
            'name': _('The name of the assignment'),
            'description': _('A short description of the excercises'),
            'can_studentsubmit': _('Student can submit earlier'),
            'remove_collected': _('Remove folder when collecting'),
        }
        help_texts = {
            'can_studentsubmit': _('Student can submit earlier even when you set an expiry date.'),
            'remove_collected': _('Remove student\'s folder when submitted'),
        }

    def __init__(self, *args, **kwargs):
        course = kwargs.pop('course', None)
        user = kwargs.pop('user', None)
        super(FormAssignment, self).__init__(*args, **kwargs)
        self.fields["folder"].choices = map(lambda x: (x, x), course.dir_assignmentcandidate())
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
        self.fields['folder'].widget.attrs["class"] = "form-select"
        self.fields['can_studentsubmit'].widget.attrs["class"] = "form-check-input"
        self.fields['can_studentsubmit'].widget.attrs["style"] = ""
        self.fields['remove_collected'].widget.attrs["class"] = "form-check-input"
        self.fields['remove_collected'].widget.attrs["style"] = ""
        self.fields['valid_from'].widget.attrs["class"] = "form-control datetimepicker span2"
        self.fields['expires_at'].widget.attrs["class"] = "form-control datetimepicker span2"

