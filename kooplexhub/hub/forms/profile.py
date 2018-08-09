from django import forms
from django.utils.translation import gettext_lazy as _

from hub.models import Profile

class FormBiography(forms.ModelForm):

    class Meta:
        model = Profile
        fields = ['location', 'bio', ]
        labels = {
            'location': _('Your location'),
            'bio': _('Short cv'),
        }
        help_texts = {
            'location': _('Where most often you can be found when at work.'),
            'bio': _('Some words about you and your work of interest that distinguishes you.'),
        }

    def __init__(self, *args, **kwargs):
        super(FormBiography, self).__init__(*args, **kwargs)
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
