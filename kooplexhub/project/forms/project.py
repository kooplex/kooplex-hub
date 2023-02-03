import json
from django import forms
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.db.models import Q
from django.contrib.auth.models import User

from kooplexhub.lib import my_slug_validator, my_end_validator, my_alphanumeric_validator
from container.models import Container, Image
from ..models import Project, UserProjectBinding

from kooplexhub.lib import my_slug_validator, my_end_validator
from kooplexhub.common import tooltip_attrs


class FolderTextWidget(forms.TextInput):
    template_name = 'folder.html'


class FormProject(forms.ModelForm):
    class Meta:
        model = Project
        fields = [ 'name', 'subpath', 'description', 'scope', 'preferred_image' ]

    project_config = forms.CharField(widget = forms.HiddenInput(), required = False)
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
    description = forms.CharField(
        max_length = 100, required = True,
        widget = forms.Textarea(attrs = tooltip_attrs({
            'rows': 3, 
            'title': _('It is always a good idea to have a short but straight to the point abstract of your project.'), 
        })),
    )
    scope = forms.ChoiceField(
        choices = Project.SCP_LOOKUP.items(), required = True,
        widget = forms.Select(attrs = tooltip_attrs({ 'title': _('Select the scope of the project') }))
    )
    preferred_image = forms.ModelChoiceField(
        label = _('Image'),
        queryset = Image.objects.filter(imagetype = Image.TP_PROJECT, present = True), 
        required = False, empty_label = 'Select image...',
        widget = forms.Select(attrs = tooltip_attrs({ 'title': _('Select an image if you prefer an environment to be created.') })),
    )
    def descriptions(self):
        hidden = lambda i: f"""<input type="hidden" id="image-description-{i.id}" value="{i.description}">"""
        return format_html("".join(list(map(hidden, self.fields['preferred_image'].queryset))))


    def __init__(self, *args, **kwargs):
        from ..forms import TableCollaborator, TableContainer
        user = kwargs['initial'].get('user')
        super().__init__(*args, **kwargs)
        project = kwargs.get('instance', Project())
        self.t_users = TableCollaborator(project, user, collaborator_table = False)
        self.t_collaborators = TableCollaborator(project, user, collaborator_table = True)
        self.t_services = TableContainer(user = user, project = project)
        if project.id:
            self.fields['subpath'].disabled = True

    def clean(self):
        cleaned_data = super().clean()
        extra = json.loads(cleaned_data['project_config'])
        projectid = extra.get('project_id')
        userid = extra.get('user_id')
        projectname = cleaned_data.get('name')
        subpath = cleaned_data.get('subpath')
        ve = []
        if not subpath:
            ve.append( forms.ValidationError(_(f'Project folder cannot be empty'), code = 'invalid subpath') )
        if not projectname:
            ve.append( forms.ValidationError(_(f'Project name cannot be empty'), code = 'invalid projectname') )
        if projectid:
            if Project.objects.filter(subpath = subpath).exclude(id = projectid):
                ve.append( forms.ValidationError(_(f'Project folder {subpath} is not unique'), code = 'invalid subpath') )
            if UserProjectBinding.objects.filter(user__id = userid, project__name = projectname).exclude(project__id = projectid):
                ve.append( forms.ValidationError(_(f'Project name {projectname} is not unique'), code = 'invalid projectname') )
        else:
            if Project.objects.filter(subpath = subpath):
                ve.append( forms.ValidationError(_(f'Project folder {subpath} is not unique'), code = 'invalid subpath') )
            if UserProjectBinding.objects.filter(user__id = userid, project__name = projectname):
                ve.append( forms.ValidationError(_(f'Project name {projectname} is not unique'), code = 'invalid projectname') )
        if ve:
            raise forms.ValidationError(ve)
        cleaned_data['project_config'] = {
            'user_id': extra['user_id'],
            'project_id': extra['project_id'],
            'bind_containers': Container.objects.filter(id__in = extra['bind_container_ids'], user__id = userid),
            'collaborators': User.objects.filter(id__in = extra['bind_user_ids']),
            'admins': User.objects.filter(id__in = extra['bind_user_ids']).filter(id__in = extra['admin_users']),
        }
        return cleaned_data


class FormJoinProject(forms.Form):
    join = forms.CharField(widget = forms.HiddenInput(), required = False)

    def __init__(self, *argv, **kwargs):
        from ..forms import TableJoinProject   #, TableCollaborator, TableContainer
        user = kwargs['initial'].pop('user')
        super().__init__(*argv, **kwargs)
        joinable_bindings = UserProjectBinding.objects.filter(project__scope__in = [ Project.SCP_INTERNAL, Project.SCP_PUBLIC ], role = UserProjectBinding.RL_CREATOR).exclude(user = user)
        joined_projects = [ upb.project for upb in UserProjectBinding.objects.filter(user = user, role__in = [ UserProjectBinding.RL_ADMIN, UserProjectBinding.RL_COLLABORATOR ]) ]
        joinable_bindings = joinable_bindings.exclude(Q(project__in = joined_projects))
        self.t_joinable = TableJoinProject(joinable_bindings)

    def clean(self):
        cleaned_data = forms.Form.clean(self)
        join_info = json.loads(cleaned_data['join'])
        user = User.objects.get(id = join_info['user_id'])
        for project_id in join_info.get('join_project_ids', []):
            project = Project.objects.get(id = project_id, scope__in = [ Project.SCP_INTERNAL, Project.SCP_PUBLIC ])
            UserProjectBinding.objects.create(user = user, project = project, role = UserProjectBinding.RL_COLLABORATOR)
            #FIXME: feedback, save method?
        return cleaned_data


