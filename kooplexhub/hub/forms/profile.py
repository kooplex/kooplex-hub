from django import forms
from django.utils.translation import gettext_lazy as _

from hub.models import Profile


class FormBiography(forms.ModelForm):
    username = forms.CharField(max_length = 20, disabled = True)

    class Meta:
        model = Profile
        fields = [ 'location', 'bio', ]
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
        self.fields['bio'].widget.attrs['rows'] = 6
        self.fields['bio'].widget.attrs['cols'] = 20
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
        self.fields['username'].initial = kwargs['instance'].user.username if 'instance' in kwargs else 'unknown'

    def save(self, **kw):
        del self.fields['username']
        super(FormBiography, self).save(**kw)
