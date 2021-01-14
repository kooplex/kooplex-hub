from django import forms
from django.utils.translation import gettext_lazy as _

from hub.models import Image

class FormService(forms.Form):
    name = forms.CharField(max_length = 100, help_text = _('A short name you recall your project, but it has to be unique among your container names.'), required = True)
    image = forms.ModelChoiceField(queryset = Image.objects.filter(imagetype = Image.TP_PROJECT), help_text = _('Please select an image to the new container environment.'), required = True)

    def __init__(self, *args, **kwargs):
        super(FormService, self).__init__(*args, **kwargs)
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


