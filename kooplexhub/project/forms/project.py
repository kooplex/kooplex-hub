from django import forms
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html

from kooplexhub.lib import my_slug_validator, my_end_validator, my_alphanumeric_validator
from container.models import Container, Image
from ..models import Project, UserProjectBinding

from kooplexhub.lib import my_slug_validator, my_end_validator
from kooplexhub.common import tooltip_attrs


class FolderTextWidget(forms.TextInput):
    template_name = 'folder.html'


class FormProject(forms.Form):
    userid = forms.IntegerField(
        widget = forms.HiddenInput(),
    )
    projectid = forms.IntegerField(
        widget = forms.HiddenInput(), required = False
    )
    name = forms.CharField(
        label = _("Project name"),
        max_length = 200, required = True, 
        widget = forms.TextInput(attrs = tooltip_attrs({ 'title': _('Name your project. No worries later you can rename it.') })),
    )
    subpath = forms.CharField(
        label = _("Folder name"),
        validators = [
            my_slug_validator('Enter a valid folder name containing only small letters, numbers or underscore.'),
        ],
        max_length = 200, required = True,
        widget = FolderTextWidget(attrs = tooltip_attrs({
            'title': _('This folder is created for the project, which has to be unique. The folder name is constant for the project\'s lifetime. If left empty it is generated from the project name and username.'), 
        })),
    )
    scope = forms.ChoiceField(
        choices = Project.SCP_LOOKUP.items(), required = True,
        widget = forms.Select(attrs = tooltip_attrs({ 'title': _('Select the scope of the project') }))
    )
    description = forms.CharField(
        max_length = 100, required = True,
        widget = forms.Textarea(attrs = tooltip_attrs({
            'rows': 3, 
            'title': _('It is always a good idea to have a short but straight to the point abstract of your project.'), 
        })),
    )

    def clean(self):
        cleaned_data = super().clean()
        projectid = cleaned_data.get('projectid', None)
        userid = cleaned_data['userid']
        projectname = cleaned_data.get('name')
        subpath = cleaned_data.get('subpath')
        ve = []
        if subpath and Project.objects.filter(subpath = subpath).exclude(id = projectid):
            ve.append( forms.ValidationError(_(f'Project folder {subpath} is not unique'), code = 'invalid subpath') )
        if projectname and UserProjectBinding.objects.filter(user__id = userid, project__name = projectname).exclude(project__id = projectid):
            ve.append( forms.ValidationError(_(f'Project name {projectname} is not unique'), code = 'projectname not unique') )
        if ve:
            raise forms.ValidationError(ve)
        return cleaned_data

    def __init__(self, *args, **kwargs):
        project = kwargs.pop('project', None)
        user = kwargs.pop('user', None)
        if project:
            args = ({'projectid': project.id, 'name': project.name, 'description': project.description, 'subpath': 'dummy', 'scope': project.scope, 'userid': user.id }, )
        super().__init__(*args, **kwargs)
        if project:
            self.fields['subpath'].widget = forms.HiddenInput()


class FormProjectWithContainer(FormProject):
    environments = forms.ModelMultipleChoiceField(
        queryset = Container.objects.all(), required = False,
        widget = forms.SelectMultiple(attrs = tooltip_attrs({ 'title': _('Select an environment in which the new project is available. If none is selected we create a new default for you.') })),
    )
    image = forms.ModelChoiceField(
        queryset = Image.objects.filter(imagetype = Image.TP_PROJECT, present = True), 
        required = False, empty_label = 'Select image...',
        widget = forms.Select(attrs = tooltip_attrs({ 'title': _('Select an image if you prefer an environment to be created.') })),
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
        self.fields['environments'].choices = kwargs['initial']['environments']
