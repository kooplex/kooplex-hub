from django import forms
from django.utils.translation import gettext_lazy as _

from hub.models import Report

# Todo: dynamic update of files list
# https://simpleisbetterthancomplex.com/tutorial/2018/01/29/how-to-implement-dependent-or-chained-dropdown-list-with-django.html

class FormReport(forms.ModelForm):
    folder = forms.ChoiceField(
            help_text = _('A snapshot will be created of all files in the selected folder.')
        )
    index = forms.ChoiceField(
            help_text = _('A snapshot will be created of all files in the selected folder.'),
            label= _('Index file')
        )
    password = forms.CharField(required = False)
    tag_name = forms.CharField(
            help_text = _('You will have a separate url fo this version of the report. Tag should one word without any special characters.'),
            label= _('Tag'),
            required = False
        )
    subcategory_name = forms.CharField(
            help_text = _('When reports are listed it will be in this subcategory. Subcategory should one word without any special characters.'),
            label= _('Subcategory'),
            required = False,
            initial = 'Default'
        )

    class Meta:
        model = Report
        fields = [ 'name', 'description', 'reporttype', 'folder', 'index', 'image', 'scope', 'password', 'tag_name', 'subcategory_name' ]
        labels = {
            'name': _('The name of your report'),
            'description': _('A short description'),
            'reporttype': _('Type of report'),
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
        self.fields['image'].empty_label = None
        self.fields["description"].widget.attrs["rows"] = 3
        self.fields["description"].widget.attrs["cols"] = 20
        folders = list(user.profile.dirs_reportprepare())
        files = []
        #files = list(user.profile.files_reportprepare())
        if len(folders):
            C_folder = zip(folders, folders)
            self.fields["folder"].choices = C_folder
        #if len(files):
        #    C_files = zip(files, files)
        #    self.fields["index"].choices = C_files
        #    self.fields["index"].widget.attrs["style"] = "width: 27ex"
        for field in self.fields.keys():
            self.fields[field].widget.attrs["class"] = "form-control"

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

