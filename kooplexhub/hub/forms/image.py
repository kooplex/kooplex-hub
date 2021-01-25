from django import forms
from django.utils.translation import gettext_lazy as _

from hub.models import Image

class FormImage(forms.ModelForm):
    #FIXME: proxy!!!

    class Meta:
        model = Image
        fields = [ 'name', 'description', 'imagetype', 'dockerfile' ]
        #labels = {
        #    'location': _('Your location'),
        #    'bio': _('Short cv'),
        #}
        help_texts = {
            'name': _('Image name must be unique.'),
            'description': _('It is always a nice idea to describe the image'),
            'imagetype': _('Project images are interactive environments accessible from the hub. Report images serve for reporting.'),
            'dockerfile': _('Images are compiled from kooplex base image.'),
        }

    def __init__(self, *args, **kwargs):
        super(FormImage, self).__init__(*args, **kwargs)
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
        #self.fields['username'].initial = kwargs['instance'].user.username if 'instance' in kwargs else 'unknown'

    #def save(self, **kw):
    #    del self.fields['username']
    #    super(FormBiography, self).save(**kw)
