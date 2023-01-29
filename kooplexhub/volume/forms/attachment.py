from django import forms
from django.utils.translation import gettext_lazy as _
from django.core import validators 

from ..models import Volume

from kooplexhub.lib import my_slug_validator, my_end_validator, my_alphanumeric_validator


class FormAttachment(forms.ModelForm):
    class Meta:
        model = Volume
        fields = [ 'folder', 'description' ]

    description = forms.CharField(
        required = True,            
        widget = forms.Textarea(attrs = {
            'rows': 6, 'cols': 20,
            'class': 'form-control',
            'data-toggle': 'tooltip', 
            'title': _('It is always a nice idea to describe attachments'),
            'data-placement': 'bottom',
            })
        )
    folder = forms.CharField(
        label = _("Folder name"), required = True,            
        validators = [
            my_slug_validator('Enter a valid folder name containing only letters, numbers or dash.'),
            my_end_validator('Enter a valid folder name ending with a letter or number.'),
            ],
        widget = forms.TextInput(attrs = {
            'class': 'form-control',
            'data-toggle': 'tooltip', 
            'title': _('A unique folder name, which serves as the mount point.'),
            'data-placement': 'bottom',
            })
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
        cleaned_data['scope'] = Volume.SCP_ATTACHMENT
        #FIXME: cleaned_data['claim'] = 'TBA'
        return cleaned_data


class FormAttachmentUpdate(forms.ModelForm):
    class Meta:
        model = Volume
        fields = [ 'id', 'folder', 'description' ]

    id = forms.IntegerField(widget = forms.HiddenInput())
    description = forms.CharField(
        required = True,            
        widget = forms.Textarea(attrs = {
            'rows': 6, 'cols': 20,
            'class': 'form-control',
            'data-toggle': 'tooltip', 
            'title': _('It is always a nice idea to describe attachments'),
            'data-placement': 'bottom',
            })
        )
    folder = forms.CharField(
        disabled = True,
        widget = forms.TextInput(attrs = {
            'class': 'form-control',
            })
        )

    def clean(self):
        cleaned_data = super().clean()
        if not 'description' in cleaned_data:
            raise forms.ValidationError(_('Description seems to be practically empty'), code = 'description error')
        return cleaned_data

