from django import forms
from django.utils.translation import gettext_lazy as _

from hub.models import Service, Image, Project


class FormProject(forms.Form):
    scope = forms.ChoiceField(choices = Project.SCP_LOOKUP.items(), help_text = _('Select the scope of the project'), required = True)
    name = forms.CharField(max_length = 100, help_text = _('A short name you recall your project, but it has to be unique among your project names.'), required = True)
    description = forms.CharField(max_length = 100, help_text = _('It is always a good idea to have an abstract of your project.'), widget = forms.Textarea, required = True)
    environments = forms.ModelMultipleChoiceField(queryset = None, help_text = _('Select an environment in which the new project is available. If none is selected we create a new default for you.'), required = False)
    image = forms.ModelChoiceField(queryset = Image.objects.filter(imagetype = Image.TP_PROJECT), help_text = _('Select an image if you prefer an environment to be created.'), required = False)

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user')
        super().__init__(*args, **kwargs)
        self.fields['environments'].queryset = Service.objects.filter(user = user)
        self.fields['description'].widget.attrs.update({ 'rows': 3, 'cols': 30 })
        for field in self.fields:
            help_text = self.fields[field].help_text
            self.fields[field].help_text = None
            #self.fields[field].widget.attrs["class"] = "form-control"
            if help_text != '':
                extra = {
                    'data-toggle': 'tooltip', 
                    'title': help_text,
                    'data-placement': 'bottom',
                }
                self.fields[field].widget.attrs.update(extra)
