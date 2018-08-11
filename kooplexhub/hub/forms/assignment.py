from django import forms
from django.utils.translation import gettext_lazy as _

from hub.models import Assignment

class FormAssignment(forms.ModelForm):
    folder = forms.ChoiceField(
            help_text = _('A snapshot will be created of all files in the selected folder, and students will receive a copy of this snapshot.')
        )
    valid_from = forms.DateTimeField(
            input_formats = ["%m/%d/%y %H:%M"], 
            widget = forms.DateTimeInput(attrs = { "class": "datetimepicker" }), 
            required = False, 
            help_text = _('If unspecified the assignment folder is populated to students right away.'),
        )
    expires_at = forms.DateTimeField(
            input_formats = ["%m/%d/%y %H:%M"], 
            widget = forms.DateTimeInput(attrs = { "class": "datetimepicker" }), 
            required = False,
            help_text = _('If unspecified either you or students need to take care of collecting or submitting assignments respectively.'),
        )

    class Meta:
        model = Assignment
        fields = [ 'name', 'folder', 'description', 'can_studentsubmit', 'is_massassignment', 'valid_from', 'expires_at', ]
        labels = {
            'name': _('The name of the assignment'),
            'description': _('A short description of the excercises'),
            'can_studentsubmit': _('Student can submit earlier'),
            'is_massassignment': _('All students receive'),
        }
        help_texts = {
            'can_studentsubmit': _('Student can submit earlier even when you set an expiry date.'),
            'is_massassignment': _('All students receive the same set of excercises.'),
        }

    def __init__(self, *args, **kwargs):
        course = kwargs.pop('course', None)
        user = kwargs.pop('user', None)
        super(FormAssignment, self).__init__(*args, **kwargs)
        self.fields["description"].widget.attrs["rows"] = 3
        self.fields["description"].widget.attrs["cols"] = 20
        if course is not None:
            C_folder = zip(course.dirs_assignmentcandidate(), course.dirs_assignmentcandidate())
            self.fields["folder"].choices = C_folder
            self.fields["folder"].widget.attrs["style"] = "width: 27ex"
            if user is not None:
                C_flags = []
                for flag in course.lookup_usercourseflags(user):
                    C_flags.append( (flag, "%s (%d students)" % (flag, course.count_students4flag(flag))) )
                self.fields["flags"] = forms.MultipleChoiceField(label = "Courses", choices = C_flags, help_text = _('Select those courses for which this assignment applies for.'))
                self.fields["flags"].widget.attrs["style"] = "width: 27ex"
        for field in self.fields:
            help_text = self.fields[field].help_text
            self.fields[field].help_text = None
            if help_text != '':
                extra = {
                    'data-toggle': 'tooltip', 
                    'title': help_text,
                    'data-placement': 'bottom',
                }
                self.fields[field].widget.attrs.update(extra)

