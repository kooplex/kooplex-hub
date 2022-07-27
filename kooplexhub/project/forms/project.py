from django import forms
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html

from kooplexhub.lib import my_slug_validator, my_end_validator, my_alphanumeric_validator
from container.models import Container, Image
from ..models import Project, UserProjectBinding

from kooplexhub.lib import my_slug_validator, my_end_validator


class FormProject(forms.Form):
    userid = forms.IntegerField()
    projectid = forms.IntegerField(required = False)
    name = forms.CharField(
            label = _("Project name"),
            help_text = _('Name your project. No worries later you can rename your project.'), 
            max_length = 200, required = True, 
            )
    subpath = forms.CharField(
            label = _("Folder name"),
            help_text = _('This folder is created for the project, which has to be unique. The folder name is constant for the project\'s lifetime. If left empty it is generated from the project name and username.'), 
            validators = [
                my_slug_validator('Enter a valid folder name containing only letters, numbers or dash.'),
            ],
            max_length = 200, required = False,
            )
    scope = forms.ChoiceField(choices = Project.SCP_LOOKUP.items(), help_text = _('Select the scope of the project'), required = True)
    description = forms.CharField(
            max_length = 100, required = True,
            help_text = _('It is always a good idea to have a short but straight to the point abstract of your project.'), 
            widget = forms.Textarea(attrs = {'rows': 3 }),
            )

    def clean(self):
        cleaned_data = super().clean()
        projectid = cleaned_data.get('projectid', None)
        userid = cleaned_data['userid']
        projectname = cleaned_data['name'].strip()
        subpath = cleaned_data['subpath'].strip()
        if Project.objects.filter(subpath = subpath).exclude(id = projectid):
            raise forms.ValidationError(_(f'Project folder {subpath} is not unique'), code = 'invalid subpath')
        if UserProjectBinding.objects.filter(user__id = userid, project__name = projectname).exclude(project__id = projectid):
            raise forms.ValidationError(_(f'Project name {projectname} is not unique'), code = 'projectname not unique')
        cleaned_data['name'] = projectname
        cleaned_data['subpath'] = subpath   
        return cleaned_data

    def __init__(self, *args, **kwargs):
        project = kwargs.pop('project', None)
        user = kwargs.pop('user', None)
        if project:
            args = ({'projectid': project.id, 'name': project.name, 'description': project.description, 'subpath': 'dummy', 'scope': project.scope, 'userid': user.id }, )
        super().__init__(*args, **kwargs)
        if project:
            self.fields['subpath'].widget = forms.HiddenInput()
        self.fields['projectid'].widget = forms.HiddenInput()
        self.fields['userid'].widget = forms.HiddenInput()
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

class FormProjectWithContainer(FormProject):
    environments = forms.ModelMultipleChoiceField(
        queryset = None, required = False,
        help_text = _('Select an environment in which the new project is available. If none is selected we create a new default for you.'), 
    )
    image = forms.ModelChoiceField(
        queryset = Image.objects.filter(imagetype = Image.TP_PROJECT, present = True), 
        help_text = _('Select an image if you prefer an environment to be created.'), required = False, empty_label = 'Select image...'
    )

    def descriptions(self):
        hidden = lambda i: f"""<input type="hidden" id="image-description-{i.id}" value="{i.description}">"""
        return format_html("".join(list(map(hidden, self.fields['image'].queryset))))

    def clean(self):
        cleaned_data = super().clean()
        if len(cleaned_data['environments']) > 0 and cleaned_data['image']:
            raise forms.ValidationError(_("either select an image or select some environments"), code = 'contradictory request')
        if len(cleaned_data['environments']) == 0 and not cleaned_data['image']:
            raise forms.ValidationError(_("either select an image or select some environments"), code = 'contradictory request')
        return cleaned_data

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['environments'].queryset = kwargs['initial']['environments']
