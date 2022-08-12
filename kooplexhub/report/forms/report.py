from django import forms

from django.utils.translation import gettext_lazy as _

from ..models import Report
from container.models import Image
from project.models import Project
from ..filesystem import dir_reportcandidate

class MyDescription(forms.Textarea):
    def __init__(self, *args, **kwargs):
        super(MyDescription, self).__init__(*args, **kwargs)
        self.attrs['rows'] = 3
        self.attrs['cols'] = 30


class FormReport(forms.ModelForm):
    folder = forms.ChoiceField(
            help_text = _('The content of the folder serves for the report.'),
        )
    description = forms.CharField(
            max_length = 100, required = True,
            help_text = _('It is always a good idea to have an abstract of your report.'), 
            widget = MyDescription, 
        )


    class Meta:
        model = Report
        fields = [ 'name', 'folder', 'description', 'is_static', 'scope', 'image', 'index' ]
        labels = {
            'name': _('The name of the report'),
            'description': _('A short description of the report'),
        }
        help_texts = {
            'scope': _('Decide who can see the report'),
            'is_static': _('Static report served by an nginx server')
        }

    def __init__(self, *args, **kwargs):
        project = kwargs.pop('project', Project.objects.first())
        user = kwargs.pop('user', None)
        super(FormReport, self).__init__(*args, **kwargs)
        folders = dir_reportcandidate(project)
        self.fields["folder"].choices = map(lambda x: (x, x), folders)
        #images = Image.objects.filter(imagetype=Image.TP_REPORT)
        #self.fields["image"].choices = map(lambda x: (x, x), images)
        for field in self.fields:
            help_text = self.fields[field].help_text
            self.fields[field].help_text = None
            if field == 'is_static':
                self.fields[field].widget.attrs["class"] = "form-check-input"
                self.fields[field].widget.attrs["style"] = ""
            else:
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

        self.project = project
        self.okay = len(folders) > 0


class FormReportConfigure(forms.ModelForm):
    description = forms.CharField(
            max_length = 100, required = True,
            help_text = _('It is always a good idea to have an abstract of your report.'), 
            widget = MyDescription, 
        )


    class Meta:
        model = Report
        fields = [ 'name', 'description', 'is_static', 'scope', 'image', 'index', 'creator', 'folder', 'project' ]
        labels = {
            'name': _('The name of the report'),
            'description': _('A short description of the report'),
        }
        help_texts = {
            'scope': _('Decide who can see the report'),
            'is_static': _('Static report served by an nginx server')
        }

    def __init__(self, *args, **kwargs):
        super(FormReportConfigure, self).__init__(*args, **kwargs)
        for field in self.fields:
            help_text = self.fields[field].help_text
            self.fields[field].help_text = None
            if field == 'is_static':
                self.fields[field].widget.attrs["class"] = "form-check-input"
                self.fields[field].widget.attrs["style"] = ""
            elif field in [ 'creator', 'project', 'folder' ]:
                self.fields[field].widget = forms.HiddenInput()
            else:
                self.fields[field].widget.attrs["class"] = "form-control"
                self.fields[field].widget.attrs["style"] = "width: 100%"
            if help_text != '':
                extra = {
                    'data-toggle': 'tooltip', 
                    'title': help_text,
                    'data-placement': 'bottom',
                }
                self.fields[field].widget.attrs.update(extra)


