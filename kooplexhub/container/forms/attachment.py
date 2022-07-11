from django import forms
from django.utils.translation import gettext_lazy as _
from django.core import validators 

from ..models import Attachment

from kooplexhub.lib import my_slug_validator, my_end_validator, my_alphanumeric_validator


class FormAttachment(forms.ModelForm):

    class Meta:
        model = Attachment
        fields = [ 'name', 'description', 'folder' ]
        help_texts = {
            'name': _('Attachment name must be unique.'),
            'description': _('It is always a nice idea to describe attachments'),
            'folder': _('A unique folder name, which serves as the mount point.'),
        }

    def clean(self):
        cleaned_data = super().clean()
        name = cleaned_data['name'].strip()
        folder = cleaned_data['folder'].strip()
        if len(Attachment.objects.filter(folder = folder)) != 0:
            raise forms.ValidationError(_(f'Attachment folder {folder} is not unique'), code = 'invalid folder')
        if len(Attachment.objects.filter(name = name)) != 0:
            raise forms.ValidationError(_(f'Attachment name {name} is not unique'), code = 'attachmentname not unique')
        cleaned_data['name'] = name
        cleaned_data['folder'] = folder   
        return cleaned_data


    def __init__(self, *args, **kwargs):
        super(FormAttachment, self).__init__(*args, **kwargs)
        self.fields['name'] = forms.CharField(
                label = _("Attachment name"),
                required = True,            
                validators = [
                    my_alphanumeric_validator('Enter a valid attachment name containing only letters and numbers.'),
                ],

            )
        self.fields['description'].widget.attrs['rows'] = 6
        self.fields['description'].widget.attrs['cols'] = 20
        self.fields['folder'] = forms.CharField(
                label = _("Folder name"),
                required = True,            
                validators = [
                    my_slug_validator('Enter a valid folder name containing only letters, numbers or dash.'),
                    my_end_validator('Enter a valid folder name ending with a letter or number.'),
                ],

            )
        self.fields['folder'].widget.attrs['cols'] = 20
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

