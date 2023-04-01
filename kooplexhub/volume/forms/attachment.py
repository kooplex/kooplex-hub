from django import forms
from django.utils.translation import gettext_lazy as _
from django.core import validators 

from ..models import Volume

from kooplexhub.settings import KOOPLEX
from kooplexhub.lib import my_slug_validator, my_end_validator, my_alphanumeric_validator
from kooplexhub.common import tooltip_attrs


claim_attachment = KOOPLEX.get('userdata', {}).get('claim-attachment', 'attachments')

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
        cleaned_data['scope'] = Volume.SCP_ATTACHMENT
        cleaned_data['claim'] = claim_attachment
        return cleaned_data


class FormVolumeUpdate(FormAttachment):
    class Meta:
        model = Volume
        fields = [ 'id', 'folder', 'description', 'scope' ]

    id = forms.IntegerField(widget = forms.HiddenInput())
    shared = forms.CharField(widget = forms.HiddenInput(), required = False)

    def clean(self):
        cleaned_data = forms.ModelForm.clean(self)
        return cleaned_data

    def __init__(self, *argv, **kwargs):
        from ..forms import TableVolumeShare
        user = kwargs.pop('user')
        super().__init__(*argv, **kwargs)
        self.fields['folder'].disabled = True
        instance = kwargs.get('instance')
        if instance.scope == instance.SCP_ATTACHMENT:
            self.fields['scope'].widget = forms.HiddenInput()
            self.fields['scope'].value = instance.SCP_ATTACHMENT,
        else:
            self.fields['scope'].widget = forms.Select(attrs = tooltip_attrs({ 'title': _('Change the scope of this volume.'), }))
            self.fields['scope'].widget.choices = list(filter(lambda s: s[0] != instance.SCP_ATTACHMENT, instance.SCP_LOOKUP.items()))
            self.t_users = TableVolumeShare(instance, user, collaborator_table = False)
            self.t_collaborators = TableVolumeShare(instance, user, collaborator_table = True)
