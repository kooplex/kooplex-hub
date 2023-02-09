import json
from django import forms
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html

from django.contrib.auth.models import User
from ..models import Container, Image
from project.models import Project
from volume.models import Volume
from education.models import Course

from kooplexhub.lib import my_alphanumeric_validator
from kooplexhub.common import tooltip_attrs


class myNumberInput(forms.NumberInput):
    template_name = 'widget_decimal.html'

class FormContainer(forms.ModelForm):
    class Meta:
        model = Container
        fields = [ 'user', 'friendly_name', 'image', 'node', 'idletime', 'cpurequest', 'gpurequest', 'memoryrequest' ]

    container_config = forms.CharField(widget = forms.HiddenInput(), required = False)
    user = forms.CharField(widget = forms.HiddenInput(), required = True)
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
        min_value=0.1, #max_value=1, 
        widget = myNumberInput(attrs = tooltip_attrs({
            'title': _('Requested number of cpus for your container.'), 
            'step': 0.1,
        }))
    )

    gpurequest = forms.IntegerField(
        label = 'GPU [#]', required = False,
        min_value=0, #max_value=1,
        widget = myNumberInput(attrs = tooltip_attrs({
            'title': _('Requested number of gpus for your container.'), 
        }))
    )

    memoryrequest = forms.DecimalField(
        label = 'Memory [GB]', required = False,
        min_value=0.1, #max_value=1, 
        widget = myNumberInput(attrs = tooltip_attrs({
            'title': _('Requested memory for your container.'), 
            'step': 0.1
        }))
    )


    def descriptions(self):
        import base64
        hidden = lambda i: f"""
<input type="hidden" id="image-description-{i.id}" value="{i.description}">
<input type="hidden" id="image-thumbnail-{i.id}" value="{i.thumbnail.img_src}">
        """
        return format_html("".join(list(map(hidden, self.fields['image'].queryset))))


    def __init__(self, *args, **kwargs):
        from ..forms import TableContainerProject, TableContainerCourse, TableContainerVolume
        user = kwargs['initial'].get('user')
        nodes = kwargs.pop('nodes', None)
        super().__init__(*args, **kwargs)
        container = kwargs.get('instance', Container())
        self.t_projects = TableContainerProject(container, user)
        self.t_courses = TableContainerCourse(container, user)
        self.t_volumes = TableContainerVolume(container, user)
        if container.id:
            pass
        if nodes:
            self.fields['node'].choices = [('', '')] + [ (x, x) for x in nodes ]
            if container:
                self.fields['node'].value = container.node
        else:
            self.fields['node'].widget = forms.HiddenInput()

    def clean(self):
        cleaned_data = super().clean()
        extra = json.loads(cleaned_data['container_config'])
        containerid = extra.get('container_id')
        userid = extra.get('user_id')
        user = User.objects.get(id = userid)
        containername = cleaned_data.get('friendly_name') #FIXME
        ve = []
        if not containername:
            ve.append( forms.ValidationError(_(f'Container name cannot be empty'), code = 'invalid name') )
        if containerid:
            pass
        else:
            if Container.objects.filter(friendly_name = containername, user__id = userid):
                ve.append( forms.ValidationError(_(f'Container name {containername} is not unique'), code = 'invalid name') )
        if ve:
            raise forms.ValidationError(ve)
        cleaned_data['user'] = user
        # authorization
        A = lambda x: list(filter(lambda i: i.is_user_authorized(user), x))
        cleaned_data['container_config'] = {
            'user_id': extra['user_id'],
            'container_id': extra['container_id'],
            'bind_projects': A(Project.objects.filter(id__in = extra['bind_project_ids'])),
            'bind_courses': A(Course.objects.filter(id__in = extra['bind_course_ids'])),
            'bind_volumes': A(Volume.objects.filter(id__in = extra['bind_volume_ids'])),
        }
        return cleaned_data

