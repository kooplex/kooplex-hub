from django import forms
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html

from ..models import Image

from kooplexhub.lib import my_alphanumeric_validator


class FormContainer(forms.Form):
    friendly_name = forms.CharField(
            max_length = 200, required = True,
            label = 'Name', #FIXME: when model refactored, ie friendly_name becomes name, it can be removed
            help_text = _('A short friendly name makes your life easier to find your container environment.'), 
            widget = forms.TextInput(attrs = {"data-intro": "#friendlyname"}) #FIXME: is it still used? was not it chardin
            )
#    name = forms.CharField(
#            max_length = 100, required = True,
#            help_text = _('A container name, the system uses to identify your environment. It has to be unique among your container names.'), 
#            validators = [
#                    my_alphanumeric_validator('Enter a valid container name containing only letters and numbers.'),
#                ],
#            widget = forms.TextInput(attrs = {"data-intro": "#name"})
#            )
    image = forms.ModelChoiceField(
            queryset = Image.objects.filter(imagetype = Image.TP_PROJECT, present = True), 
            help_text = _('Please select to associate an image to your new container environment. During selection a short description of each image is shown to help you decide.'), required = True, 
            empty_label = 'Select image...',
            )

    node = forms.ChoiceField(
            required = False,
            label = 'Node',
            help_text = _('Choose a node where to launch the environment.'), 
            )
    
    cpurequest = forms.DecimalField(
            required = False,
            label = 'CPU [#]',
            help_text = _('Requested number of cpus for your container.'), 
            min_value=0.1, max_value=1, widget=forms.NumberInput(attrs={'step': 0.1}))

    gpurequest = forms.IntegerField(
            required = False,
            label = 'GPU [#]',
            help_text = _('Requested number of gpus for your container.'), 
            min_value=0, max_value=0)

    memoryrequest = forms.DecimalField(
            required = False,
            label = 'Memory [GB]',
            help_text = _('Requested memory for your container.'), 
            min_value=0.1, max_value=1, widget=forms.NumberInput(attrs={'step': 0.1}))

    def descriptions(self):
        hidden = lambda i: f"""<input type="hidden" id="image-description-{i.id}" value="{i.description}">"""
        return format_html("".join(list(map(hidden, self.fields['image'].queryset))))


    def __init__(self, *args, **kwargs):
        container = kwargs.pop('container', None)
        nodes = kwargs.pop('nodes', None)
        if container:
#FIXME: can this piece of code be cleaner
            args = ({'friendly_name': container.friendly_name, 'image': container.image, 'node': container.node, 'cpurequest': container.cpurequest, 'gpurequest': container.gpurequest,'memoryrequest': container.memoryrequest }, )
        super(FormContainer, self).__init__(*args, **kwargs)
        if nodes:
            self.fields['node'].choices = [('', '')] + [ (x, x) for x in nodes ]
            if container:
                self.fields['node'].value = container.node
        else:
            self.fields['node'].widget = forms.HiddenInput()
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

