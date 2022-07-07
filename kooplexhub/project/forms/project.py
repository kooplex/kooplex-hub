from django import forms
from django.utils.translation import gettext_lazy as _

from kooplexhub.lib import my_slug_validator, my_end_validator, my_alphanumeric_validator
from container.models import Container, Image
from ..models import Project, UserProjectBinding

from kooplexhub.lib import my_slug_validator, my_end_validator


class MyDescription(forms.Textarea):
    def __init__(self, *args, **kwargs):
        super(MyDescription, self).__init__(*args, **kwargs)
        self.attrs['rows'] = 3
        self.attrs['cols'] = 30


class FormProject(forms.Form):
    scope = forms.ChoiceField(choices = Project.SCP_LOOKUP.items(), help_text = _('Select the scope of the project'), required = True)
    userid = forms.IntegerField()
    name = forms.CharField(
            label = _("Project name"),
            help_text = _('Name your project'), 
            max_length = 200, required = True, 
            )
    subpath = forms.CharField(
            label = _("Folder name"),
            help_text = _('This folder is created for the project, which has to be unique. If left empty it is generated from the project name and username.'), 
            validators = [
                my_slug_validator('Enter a valid folder name containing only letters, numbers or dash.'),
            ],
            max_length = 200, required = False,
            )
    description = forms.CharField(
            max_length = 100, required = True,
            help_text = _('It is always a good idea to have an abstract of your project.'), 
            widget = MyDescription, 
            )
    environments = forms.ModelMultipleChoiceField(queryset = None, required = False,
            help_text = _('Select an environment in which the new project is available. If none is selected we create a new default for you.'), 
            )
    image = forms.ModelChoiceField(queryset = Image.objects.filter(imagetype = Image.TP_PROJECT, present = True), help_text = _('Select an image if you prefer an environment to be created.'), required = False, empty_label = 'Select image...')

    def clean(self):
        cleaned_data = super().clean()
        userid = cleaned_data['userid']
        projectname = cleaned_data['name'].strip()
        subpath = cleaned_data['subpath'].strip()
        if len(Project.objects.filter(subpath = subpath)) != 0:
            raise forms.ValidationError(_(f'Project folder {subpath} is not unique'), code = 'invalid subpath')
        if len(UserProjectBinding.objects.filter(user__id = userid, project__name = projectname)) != 0:
            raise forms.ValidationError(_(f'Project name {projectname} is not unique'), code = 'projectname not unique')
        #Unsure why all env items show, how to retrieve what is selected?
        #FIXME: if len(cleaned_data['environments']) > 0 or cleaned_data['image']:
        #FIXME:     raise forms.ValidationError(_("either select an image or select some environments"), code = 'contradictory request')
        cleaned_data['name'] = projectname
        cleaned_data['subpath'] = subpath   
        return cleaned_data

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['userid'].widget = forms.HiddenInput()
        self.fields['environments'].queryset = kwargs['initial']['environments']
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
