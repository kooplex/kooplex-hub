from django import forms
from django.utils.translation import gettext_lazy as _

from education.models import Assignment

try:
    from kooplexhub.settings import KOOPLEX
except ImportError:
    KOOPLEX = {}
KOOPLEX['kubernetes'].update({})
KOOPLEX['kubernetes']['userdata'].update({})

class dateWidget(forms.DateTimeInput):
    template_name = 'datetime_pick.html'

class FormAssignment(forms.ModelForm):
    class Meta:
        model = Assignment
        fields = [ 'name', 'folder', 'description', 'remove_collected', 'max_size' ]
        sequence = [ 'name', 'folder', 'description', 'remove_collected', 'valid_from_widget', 'expires_at_widget', 'max_size' ]
        labels = {
            'name': _('The name of the assignment'),
            'description': _('A short description of the excercises'),
        }

    folder = forms.ChoiceField(
            help_text = _('A snapshot will be created of all files in the selected folder, and students will receive a copy of this snapshot.'),
        )
    description = forms.CharField(
            max_length = 100, required = True,
            help_text = _('It is always a good idea to have an abstract of your assignment.'), 
            widget = forms.Textarea(attrs = {'rows': 3 }), 
        )
    valid_from_widget = forms.DateTimeField(
            label = 'Valid from',
            input_formats = ["%m/%d/%Y, %H:%M"], 
            widget = dateWidget(attrs = { 'icon': 'bi bi-clock', 'name': 'valid_from_widget' }), 
            required = False, 
        )
    expires_at_widget = forms.DateTimeField(
            label = 'Expires at',
            input_formats = ["%m/%d/%Y, %H:%M"], 
            widget = dateWidget(attrs = { 'icon': 'bi bi-bell', 'name': 'expires_at_widget' }), 
            required = False,
        )
    remove_collected = forms.BooleanField(
            widget = forms.CheckboxInput(attrs = { 'data-size': 'small', 'data-toggle': 'toggle', 
                'data-on': "<span class='oi oi-trash'></span>", 'data-off': "<span class='bi bi-check-lg'></span>",
                'data-onstyle': "danger", 'data-offstyle': "secondary" }), 
            required = False,
        )
    max_size = forms.IntegerField(
            required = False,
            help_text = _('Total file size quota applied to the assignment.'),
        )

    def clean(self):
        cleaned_data = super().clean()
        timestamp1 = cleaned_data.pop('valid_from_widget')
        timestamp2 = cleaned_data.pop('expires_at_widget')
        #FIXME: check relation, check if time is past: ValidationError
        cleaned_data['ts_handout'] = timestamp1
        cleaned_data['ts_collect'] = timestamp2
        return cleaned_data


    def __init__(self, *args, **kwargs):
        course = kwargs.pop('course', None)
        user = kwargs.pop('user', None)
        super(FormAssignment, self).__init__(*args, **kwargs)
        folders = course.dir_assignmentcandidate()
        self.fields["folder"].choices = map(lambda x: (x, x), folders)
        for field in self.fields:
            if field in [ 'remove_collected', 'valid_from' ]:
                continue
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

        self.course = course
        self.okay = len(folders) > 0
        self.folder_usercontainer = KOOPLEX['kubernetes']['userdata'].get('mountPath_course_assignment_prepare', '/course/{course.folder}.prepare').format(course = course)


