from django import forms
from django.utils.translation import gettext_lazy as _
from django.core import validators 

from ..models import Volume

from kooplexhub.lib import my_slug_validator, my_end_validator, my_alphanumeric_validator
from kooplexhub.common import tooltip_attrs

from ..conf import VOLUME_SETTINGS


class FormAttachment(forms.ModelForm):
    class Meta:
        model = Volume
        fields = [ 'folder', 'description' ]

    description = forms.CharField(
        required = True,            
        widget = forms.Textarea(attrs = tooltip_attrs({ 
            'title': _('It is always a nice idea to describe attachments'),
        }))
    )
 
    folder = forms.CharField(
        label = _("Folder name"), required = True,            
        validators = [
            my_slug_validator('Enter a valid folder name containing only letters, numbers or dash.'),
            my_end_validator('Enter a valid folder name ending with a letter or number.'),
            ],
        widget = forms.TextInput(attrs = tooltip_attrs({ 'title': _('A unique folder name, which serves as the mount point.'), }))
    )

    def clean(self):
        cleaned_data = super().clean()
        ve = []
        if not 'folder' in cleaned_data:
            ve.append( forms.ValidationError(_(f'Folder name is practically empty'), code = 'invalid folder') )
        folder = cleaned_data.get('folder', '')
        if len(Volume.objects.filter(folder = folder)) != 0:
            ve.append( forms.ValidationError(_(f'Attachment folder {folder} is not unique'), code = 'invalid folder') )
        if ve:
            raise forms.ValidationError(ve)
        cleaned_data['subPath'] = folder
        cleaned_data['scope'] = Volume.Scope.ATTACHMENT
        cleaned_data['claim'] = VOLUME_SETTINGS["mounts"]["attachment"]["claim"]
        return cleaned_data


