from django import forms
from django.utils.translation import gettext_lazy as _

from hub.models import Attachment

class FormAttachment(forms.ModelForm):

    class Meta:
        model = Attachment
        fields = [ 'name', 'description', 'folder' ]
        help_texts = {
            'name': _('Image name must be unique.'),
            'description': _('It is always a nice idea to describe the image'),
            'folder': _('A unique folder name, which serves as the mount point.'),
        }

    def __init__(self, *args, **kwargs):
        super(FormAttachment, self).__init__(*args, **kwargs)
        self.fields['description'].widget.attrs['rows'] = 6
        self.fields['description'].widget.attrs['cols'] = 20
        for field in self.fields:
            help_text = self.fields[field].help_text
            self.fields[field].help_text = None
            self.fields[field].widget.attrs["class"] = "form-control"
            if help_text != '':
                extra = {
                    'data-toggle': 'tooltip', 
                    'title': help_text,
                    'data-placement': 'bottom',
                }
                self.fields[field].widget.attrs.update(extra)
