from django import forms
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html

from ..models import Image

from kooplexhub.lib import my_alphanumeric_validator

#class ImageSelectWidget(forms.Select):
#    template_name = 'image.html'
#    option_template_name = 'image_option.html'
#
#    def all_images(self):
#        return Image.objects.all()

    
    

class FormContainer(forms.Form):
    friendly_name = forms.CharField(
            max_length = 200, required = True,
            help_text = _('A short friendly name makes your life easier to find yout container environments'), 
            widget = forms.TextInput(attrs = {"data-intro": "#friendlyname"})
            )
    name = forms.CharField(
            max_length = 100, required = True,
            help_text = _('A container name, the system uses to identify your environment. It has to be unique among your container names.'), 
            validators = [
                    my_alphanumeric_validator('Enter a valid container name containing only letters and numbers.'),
                ],
            widget = forms.TextInput(attrs = {"data-intro": "#name"})
            )
    image = forms.ModelChoiceField(
            queryset = Image.objects.filter(imagetype = Image.TP_PROJECT, present=True), 
            help_text = _('Please select an image to the new container environment.'), required = True, 
            empty_label = 'Select image...' #, widget = ImageSelectWidget
            )

    def render_image(self, selected_choices, option_value, option_label):
        descriptions = [i.description for i in self.fields['image']]
        return u'<option value="%s"> %s %s</option>' % (
            option_value, option_value, descriptions)


    def descriptions(self):
        hidden = lambda i: f"""<input type="hidden" id="image-description-{i.id}" value="{i.description}">"""
        return format_html("".join(list(map(hidden, self.fields['image'].queryset))))


    def __init__(self, *args, **kwargs):
        super(FormContainer, self).__init__(*args, **kwargs)
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

