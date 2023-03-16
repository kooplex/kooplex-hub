import json
from django import forms
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from decimal import Decimal
from itertools import chain


from django.contrib.auth.models import User
from ..models import Container, Image
from project.models import Project
from volume.models import Volume
from education.models import Course

from kooplexhub.lib import my_alphanumeric_validator
from kooplexhub.common import tooltip_attrs
from kooplexhub.settings import KOOPLEX

from kooplexhub.lib.libbase import standardize_str

from container.lib import Cluster

def _range(attribute):
    resources_min = KOOPLEX.get('kubernetes', {}).get('resources', {}).get('requests', {})
    resources_max = KOOPLEX.get('kubernetes', {}).get('resources', {}).get('maxrequests', {})
    mapping = {
        'idletime': ('idletime', 1, 48),
        'memoryrequest': ('memory', .1, 2),
        'cpurequest': ('cpu', .1, 1),
        'gpurequest': ('nvidia.com/gpu', 0, 0),
    }
    lookup, min_default, max_default = mapping[attribute]
    return {
       'min_value': round(Decimal(resources_min.get(lookup, min_default)), 1),
       'max_value': round(Decimal(resources_max.get(lookup, max_default)), 1),
    }


def upperbound(node, container):
    if not node:
        return _range
    api = Cluster()
    api.query_nodes_status(node_list=[node], reset=True)
    api.query_pods_status(field=["spec.nodeName=",node], reset=True)
    api.resources_summary()
    from_node = api.get_data()
    mapping = {
        'cpurequest': 'avail_cpu',
        'memoryrequest': 'avail_memory',
        'gpurequest': 'avail_gpu',
    }
    if container.node == node and container.state in [ Container.ST_RUNNING, Container.ST_NEED_RESTART ]:
        #FIXME: what if ST_STARTING, ST_STOPPING?
        for k, v in mapping.items():
            from_node[v] += getattr(container, k)
    def my_range(attribute):
        from_settings = _range(attribute)
        if attribute in mapping:
            from_settings['max_value'] = round(Decimal(from_node[mapping[attribute]][0]), 1)
        return from_settings
    return my_range


class myNumberInput(forms.NumberInput):
    template_name = 'widget_decimal.html'

class FormContainer(forms.ModelForm):
    class Meta:
        model = Container
        fields = [ 'user', 'name', 'image', 'node', 'cpurequest', 'gpurequest', 'memoryrequest', 'idletime', 'start_teleport' ]

    container_config = forms.CharField(widget = forms.HiddenInput(), required = False)
    user = forms.CharField(widget = forms.HiddenInput(), required = True)
    name = forms.CharField(
        max_length = 200, required = True,
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

    node_old = forms.CharField(required = False)
    
    idletime = forms.IntegerField(
        label = 'Uptime [h]', required = False,
        **_range("idletime"),
        widget = myNumberInput(attrs = tooltip_attrs({
            'title': _('If your container resource will have been idle for longer than this interval resource system is shutting it down.'),
        }))
    )

    cpurequest = forms.DecimalField(
        label = 'CPU [#]', required = False,
        #**_range("cpurequest"), 
        min_value = _range("cpurequest")['min_value'],
        decimal_places = 1, 
        #initial = _range("cpurequest")['min_value'],
        validators = [],
        widget = myNumberInput(attrs = tooltip_attrs({
            'title': _('Requested number of cpus for your container.'), 
            'step': 0.1,
        }))
    )

    cpurequest_old = forms.CharField(required = False)

    gpurequest = forms.IntegerField(
        label = 'GPU [#]', required = False,
        #**_range("gpurequest"),
        min_value = _range("gpurequest")['min_value'],
        widget = myNumberInput(attrs = tooltip_attrs({
            'title': _('Requested number of gpus for your container.'), 
        }))
    )

    gpurequest_old = forms.CharField(required = False)

    memoryrequest = forms.DecimalField(
        label = 'Memory [GB]', required = False,
        #**_range("memoryrequest"),
        min_value = _range("memoryrequest")['min_value'],
        widget = myNumberInput(attrs = tooltip_attrs({
            'title': _('Requested memory for your container.'), 
            'step': 0.1
        }))
    )

    memoryrequest_old = forms.CharField(required = False)
   
    start_teleport = forms.BooleanField(
        widget = forms.CheckboxInput(attrs = { 'data-size': 'small', 'data-toggle': 'toggle', 
           'data-on': "<span class='bi bi-door-open'>&nbsp;ssh</span>", 'data-off': "<span class='bi bi-sign-stop'></span>",
           'data-onstyle': "success", 'data-offstyle': "secondary" }), 
        required = False,
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
        my_range = upperbound(container.node, container)
        if nodes and user.profile.can_choosenode:
            self.fields['node'].choices = [('', '')] + [ (x, x) for x in nodes ]
            if container:
                self.fields['node'].value = container.node
            for att in ['node', 'cpurequest', 'memoryrequest', 'gpurequest' ]:
                if att != 'node':
                    self.fields[att].widget.attrs['max'] = my_range(att)['max_value']
                self.fields[f"{att}_old"].widget = forms.HiddenInput()
                self.fields[f"{att}_old"].initial = getattr(container, att)
            if self.fields['gpurequest'].widget.attrs['max'] == 0:
                self.fields['gpurequest'].disabled = True
        else:
            for att in ['node', 'cpurequest', 'memoryrequest', 'gpurequest' ]:
                self.fields[att].widget = forms.HiddenInput()
        if not user.profile.can_teleport:
            self.fields['start_teleport'].disabled = True

    def clean(self):
        cleaned_data = super().clean()
        extra = json.loads(cleaned_data['container_config'])
        for att in ['node', 'cpurequest', 'memoryrequest', 'gpurequest' ]:
            cleaned_data.pop(f'{att}_old')
        containerid = extra.get('container_id')
        userid = extra.get('user_id')
        user = User.objects.get(id = userid)
        containername = cleaned_data.get('name')
        ve = []
        if not containername:
            ve.append( forms.ValidationError(_(f'Container name cannot be empty'), code = 'invalid name') )
        if containerid:
            container = Container.objects.get(id = containerid)
        else:
            if Container.objects.filter(name = containername, user = user):
                ve.append( forms.ValidationError(_(f'Container name {containername} is not unique'), code = 'invalid name') )
            cleanname = standardize_str(containername)
            cleaned_data["label"] = f'{user.username}-{cleanname}'
            container = Container()
        node = cleaned_data.pop('node', None)
        if user.profile.can_choosenode:
            cleaned_data['node'] = node if node else None
        my_range = upperbound(cleaned_data['node'], container)
        for attr in [ 'idletime', 'cpurequest', 'memoryrequest', 'gpurequest' ]:
            r = my_range(attr)
            value = cleaned_data.get(attr)
            if value:
                if value < r['min_value']:
                    ve.append( forms.ValidationError(_(f"Resource request {attr} is too small: {value} should not be less than {r['min_value']}"), code = 'invalid resource request') )
                if value > r['max_value']:
                    ve.append( forms.ValidationError(_(f"Resource request {attr} is too large: {value} should not exceed {r['min_value']}"), code = 'invalid resource request') )
            else:
                cleaned_data[attr] = r['min_value']
        cleaned_data['user'] = user
        if ve:
            raise forms.ValidationError(ve)
        # authorization
        A = lambda x: list(filter(lambda i: i.is_user_authorized(user), x))
        cleaned_data['container_config'] = {
            'user_id': extra['user_id'],
            'container_id': extra['container_id'],
            'bind_projects': A(Project.objects.filter(id__in = extra['bind_project_ids'])),
            'bind_courses': A(Course.objects.filter(id__in = extra['bind_course_ids'])),
            'bind_volumes': list(chain(A(Volume.objects.filter(id__in = extra['bind_volume_ids'])),Volume.objects.filter(id__in = extra['bind_volume_ids'], scope=Volume.SCP_ATTACHMENT) )),
            #'bind_volumes': Volume.objects.filter(id__in = extra['bind_volume_ids']),
        }
        return cleaned_data

