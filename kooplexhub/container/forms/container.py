from django import forms
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html

from ..models import Image

from kooplexhub.lib import my_alphanumeric_validator

#TODO: put somewhere common
def tooltip_attrs(attrs):
    attrs.update({
        'class': 'form-control',
        'data-toggle': 'tooltip', 
        'data-placement': 'bottom',
    })
    return attrs

class myNumberInput(forms.NumberInput):
    template_name = 'widget_decimal.html'

class FormContainer(forms.Form):
    friendly_name = forms.CharField(
        max_length = 200, required = True,
        label = 'Name', #FIXME: when model refactored, ie friendly_name becomes name, it can be removed
        widget = forms.TextInput(attrs = tooltip_attrs({
            'title': _('A short friendly name makes your life easier to find your container environment.'), 
        }))
    )

    image = forms.ModelChoiceField(
        queryset = Image.objects.filter(imagetype = Image.TP_PROJECT, present = True), 
        empty_label = 'Select image...', required = True,
        widget = forms.Select(attrs = tooltip_attrs({
            'title': _('Please select to associate an image to your new container environment. During selection a short description of each image is shown to help you decide.'), 
        }))
    )

    node = forms.ChoiceField(
        required = False,
        widget = forms.Select(attrs = tooltip_attrs({
            'title': _('Choose a node where to launch the environment.'), 
        }))
    )
    
    idletime = forms.IntegerField(
        label = 'Uptime [h]', required = False,
        min_value=1, max_value=48, 
        widget = myNumberInput(attrs = tooltip_attrs({
            'title': _('If your container resource will have been idle for longer than this interval resource system is shutting it down.'),
        }))
    )

    cpurequest = forms.DecimalField(
        label = 'CPU [#]', required = False,
        min_value=0.1, max_value=1, 
        widget = myNumberInput(attrs = tooltip_attrs({
            'title': _('Requested number of cpus for your container.'), 
            'step': 0.1,
        }))
    )

    gpurequest = forms.IntegerField(
        label = 'GPU [#]', required = False,
        min_value=0, max_value=1,
        widget = myNumberInput(attrs = tooltip_attrs({
            'title': _('Requested number of gpus for your container.'), 
        }))
    )

    memoryrequest = forms.DecimalField(
        label = 'Memory [GB]', required = False,
        min_value=0.1, max_value=1, 
        widget = myNumberInput(attrs = tooltip_attrs({
            'title': _('Requested memory for your container.'), 
            'step': 0.1
        }))
    )

    def descriptions(self):
        hidden = lambda i: f"""<input type="hidden" id="image-description-{i.id}" value="{i.description}">"""
        return format_html("".join(list(map(hidden, self.fields['image'].queryset))))


    def __init__(self, *args, **kwargs):
        container = kwargs.pop('container', None)
        nodes = kwargs.pop('nodes', None)
        if container:
            args = ({ a: getattr(container, a) for a in [ 'friendly_name', 'image', 'node', 'cpurequest', 'gpurequest','memoryrequest' ] }, )
        super(FormContainer, self).__init__(*args, **kwargs)
        if nodes:
            self.fields['node'].choices = [('', '')] + [ (x, x) for x in nodes ]
            if container:
                self.fields['node'].value = container.node
        else:
            self.fields['node'].widget = forms.HiddenInput()

