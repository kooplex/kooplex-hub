from django import forms
from django.utils.translation import gettext_lazy as _

from hub.models import Report

class FormReport(forms.ModelForm):
    folder = forms.ChoiceField(
            help_text = _('A snapshot will be created of all files in the selected folder.')
        )

    class Meta:
        model = Report
        fields = [ 'name', 'folder', 'description', 'reporttype', 'index', 'password' ]
        labels = {
            'name': _('The name of your report'),
            'description': _('A short description'),
            'index': _('Index file'),
        }
        help_texts = {
            'name': _('Report name should be unique.'),
            'description': _('It is always a good idea to have a short memo.'),
            'index': _('The name of the file the report service lands on. (Bokeh does not require it.)'),
            'password': _('Leave it empty for the public.'),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(FormReport, self).__init__(*args, **kwargs)
        self.fields["description"].widget.attrs["rows"] = 3
        self.fields["description"].widget.attrs["cols"] = 20
        folders = list(user.profile.dirs_reportprepare())
        if len(folders):
            C_folder = zip(folders, folders)
            self.fields["folder"].choices = C_folder
            self.fields["folder"].widget.attrs["style"] = "width: 27ex"
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

