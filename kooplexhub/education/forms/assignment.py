from django import forms
from django.utils.translation import gettext_lazy as _

from ..models import Assignment

try:
    from kooplexhub.settings import KOOPLEX
except ImportError:
    KOOPLEX = {}
KOOPLEX['kubernetes'].update({})
KOOPLEX['kubernetes']['userdata'].update({})



class FormAssignment(forms.ModelForm):
    folder = forms.ChoiceField(
            help_text = _('A snapshot will be created of all files in the selected folder, and students will receive a copy of this snapshot.'),
        )
    description = forms.CharField(
            max_length = 100, required = True,
            help_text = _('It is always a good idea to have an abstract of your assignment.'), 
            widget = forms.Textarea(attrs = {'rows': 3 }), 
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
    max_size = forms.IntegerField(
            required = False,
            help_text = _('Total file size quota applied to the assignment.'),
        )


    class Meta:
        model = Assignment
        fields = [ 'name', 'folder', 'description', 'remove_collected', 'valid_from', 'expires_at', 'max_size' ]
        labels = {
            'name': _('The name of the assignment'),
            'description': _('A short description of the excercises'),
            'remove_collected': _('Remove folder when collecting'),
        }
        help_texts = {
            'remove_collected': _('Remove student\'s folder when submitted'),
        }

    def __init__(self, *args, **kwargs):
        course = kwargs.pop('course', None)
        user = kwargs.pop('user', None)
        super(FormAssignment, self).__init__(*args, **kwargs)
        folders = course.dir_assignmentcandidate()
        self.fields["folder"].choices = map(lambda x: (x, x), folders)
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
        self.fields['remove_collected'].widget.attrs["class"] = "form-check-input"
        self.fields['remove_collected'].widget.attrs["style"] = ""
        self.fields['valid_from'].widget.attrs["class"] = "form-control datetimepicker span2"
        self.fields['expires_at'].widget.attrs["class"] = "form-control datetimepicker span2"

        self.course = course
        self.okay = len(folders) > 0
        self.folder_usercontainer = KOOPLEX['kubernetes']['userdata'].get('mountPath_course_assignment_prepare', '/course/{course.folder}.prepare').format(course = course)


