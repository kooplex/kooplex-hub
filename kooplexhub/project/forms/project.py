from django import forms
from django.utils.translation import gettext_lazy as _

from container.models import Container, Image
from ..models import Project

from kooplexhub.lib import my_slug_validator, my_end_validator


class MyDescription(forms.Textarea):
    def __init__(self, *args, **kwargs):
        super(MyDescription, self).__init__(*args, **kwargs)
        self.attrs['rows'] = 3
        self.attrs['cols'] = 30


class FormProject(forms.Form):
    scope = forms.ChoiceField(choices = Project.SCP_LOOKUP.items(), help_text = _('Select the scope of the project'), required = True)
    name = forms.CharField(
            label = _("Project name"),
            help_text = _('A short name you recall your project, but it has to be unique among your project names.'), 
            max_length = 100, required = True, 
            )
    description = forms.CharField(
            max_length = 100, required = True,
            help_text = _('It is always a good idea to have an abstract of your project.'), 
            widget = MyDescription, 
            )
    environments = forms.ModelMultipleChoiceField(queryset = None, required = False,
            help_text = _('Select an environment in which the new project is available. If none is selected we create a new default for you.'), 
            )
    image = forms.ModelChoiceField(queryset = Image.objects.filter(imagetype = Image.TP_PROJECT), help_text = _('Select an image if you prefer an environment to be created.'), required = False, empty_label = 'Select image...')

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user')
        super(FormProject, self).__init__(*args, **kwargs)
        self.fields['environments'].queryset = Container.objects.filter(user = user)

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

