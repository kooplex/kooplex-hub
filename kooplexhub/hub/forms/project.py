from django import forms
from django.utils.translation import gettext_lazy as _

from hub.models import Project


class FormProject(forms.ModelForm):

    class Meta:
        model = Project
        fields = [ 'name', 'description', ]
        help_texts = {
            'name': _('A short name you recall your project, but it has to be unique among your project names.'),
            'description': _('It is always a good idea to have an abstract of your project.'),
        }

    def __init__(self, *args, **kwargs):
        super(FormProject, self).__init__(*args, **kwargs)
        self.fields['name'].widget.attrs['rows'] = 1
        self.fields['name'].widget.attrs['cols'] = 20
        self.fields['description'].widget.attrs['rows'] = 6
        self.fields['description'].widget.attrs['cols'] = 20
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

