#FIXME
from django import forms
from django.utils.translation import gettext_lazy as _

from hub.models import Container


class FormContainer(forms.ModelForm):

    class Meta:
        model = Container
        fields = [ 'name', 'image' ]
        help_texts = {
            'name': _('A short name you recall your project, but it has to be unique among your container names.'),
            'image': _('Please select an image to the new container environment.'),
        }

    def __init__(self, *args, **kwargs):
        super(FormContainer, self).__init__(*args, **kwargs)
        self.fields['name'].widget.attrs['rows'] = 1
        self.fields['name'].widget.attrs['cols'] = 20
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

