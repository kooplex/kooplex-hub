from django import forms
from django.utils.translation import gettext_lazy as _
from django.core import validators 

from ..models import Attachment

from kooplexhub.lib import my_slug_validator, my_end_validator, my_alphanumeric_validator


class FormAttachment(forms.ModelForm):
    class Meta:
        model = Attachment
        fields = [ 'name', 'description', 'folder' ]

    name = forms.CharField(
        label = _("Attachment name"), required = True,            
        validators = [
            my_alphanumeric_validator('Enter a valid attachment name containing only letters and numbers.'),
        ],
        widget = forms.TextInput(attrs = {
            'class': 'form-control',
            'data-toggle': 'tooltip', 
            'title': _('Attachment name must be unique.'),
            'data-placement': 'bottom',
            })
        )
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
        name = cleaned_data['name'].strip()
        folder = cleaned_data['folder'].strip()
        if len(Attachment.objects.filter(folder = folder)) != 0:
            raise forms.ValidationError(_(f'Attachment folder {folder} is not unique'), code = 'invalid folder')
        if len(Attachment.objects.filter(name = name)) != 0:
            raise forms.ValidationError(_(f'Attachment name {name} is not unique'), code = 'attachmentname not unique')
        cleaned_data['name'] = name
        cleaned_data['folder'] = folder   
        return cleaned_data


class FormAttachmentUpdate(forms.ModelForm):
    class Meta:
        model = Attachment
        fields = [ 'id', 'name', 'description', 'folder' ]

    id = forms.IntegerField(widget = forms.HiddenInput())
    name = forms.CharField(
        label = _("Attachment name"), required = True,            
        widget = forms.TextInput(attrs = {
            'class': 'form-control',
            'data-toggle': 'tooltip', 
            'title': _('Attachment name must be unique.'),
            'data-placement': 'bottom',
            })
        )
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
        try:
            name = cleaned_data['name'].strip()
        except KeyError:
            raise forms.ValidationError(_('Name seems to be practically empty'), code = 'name error')
        try:
            description = cleaned_data['description'].strip()
        except KeyError:
            raise forms.ValidationError(_('Description seems to be practically empty'), code = 'description error')
        if Attachment.objects.filter(name = name).exclude(id = cleaned_data['id']):
            raise forms.ValidationError(_(f'Attachment name {name} is not unique'), code = 'attachmentname not unique')
        cleaned_data['name'] = name
        cleaned_data['description'] = description
        return cleaned_data

