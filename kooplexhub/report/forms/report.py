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
            max_length = 300, required = True,
            help_text = _('It is always a good idea to have an abstract of your report.'), 
            widget = MyDescription, 
        )
    name = forms.CharField(
            max_length = 25, required = True,
        )

    tags = forms.CharField(
            max_length = 25, required = True,
        )

    indexfile = forms.CharField(
            max_length = 100, required = False,
        )

    image = forms.ModelChoiceField(
            queryset = Image.objects.filter(imagetype = Image.TP_REPORT, present = True), 
            help_text = _('Please select an image for your report. During selection a short description of each image is shown to help you decide.'), required = False, 
            empty_label = 'Select image...',
            )

    class Meta:
        model = Report
        fields = [ 'name', 'folder', 'description', 'scope', 'reporttype','image', 'tags', 'indexfile' ]
        labels = {
            'name': _('Title'),
            'reporttype': _('Type'),
            'indexfile': _('Report file'),
            'description': _('A short description of the report'),
        }
        help_texts = {
            'scope': _('Decide who can see the report'),
        }

    def __init__(self, *args, **kwargs):
        project = kwargs.pop('project', Project.objects.first())
        user = kwargs.pop('user', None)
        super(FormReport, self).__init__(*args, **kwargs)
        folders = dir_reportcandidate(project)
        self.fields["folder"].choices = map(lambda x: (x, x), folders)
        self.fields["tags"].widget.attrs.update({"data-role" : "tagsinput"})
        #images = Image.objects.filter(imagetype=Image.TP_REPORT)
        #self.fields["image"].choices = map(lambda x: (x, x), images)
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

        self.project = project
        self.okay = len(folders) > 0


class FormReportConfigure(forms.ModelForm):
    description = forms.CharField(
            max_length = 300, required = True,
            help_text = _('It is always a good idea to have an abstract of your report.'), 
            widget = MyDescription, 
        )

    indexfile = forms.CharField(
            max_length = 100, required = False,
        )

    image = forms.ModelChoiceField(
            queryset = Image.objects.filter(imagetype = Image.TP_REPORT, present = True), 
            help_text = _('Please select an image for your report. During selection a short description of each image is shown to help you decide.'), required = False, 
            empty_label = 'Select image...',
            )

#    project = forms.ModelChoiceField( 
#            empty_label = 'Select project...',
#            )
#
#    reporttype = forms.ModelChoiceField( 
#            empty_label = 'Select report type...',
#            )

    class Meta:
        model = Report
        fields = [ 'name', 'description', 'scope', 'reporttype', 'image', 'creator', 'folder', 'project', 'tags', 'indexfile' ]
        labels = {
            'name': _('Title'),
            'reporttype': _('Type'),
            'indexfile': _('Report file'),
            'description': _('A short description of the report'),
        }
        help_texts = {
            'scope': _('Decide who can see the report'),
        }
        initial = {
            'name': 'Name your report (Max: 25 characteres)',
            'description': 'Describe your report (Max: 50 characteres)',
            'tags': 'Separate your tags by commas',
        }


    def __init__(self, *args, **kwargs):
        super(FormReportConfigure, self).__init__(*args, **kwargs)
        for field in self.fields:
            help_text = self.fields[field].help_text
            self.fields[field].help_text = None
            if field in [ 'creator', 'project', 'folder' ]:
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


