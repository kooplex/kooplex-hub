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
from service.models import SeafileService

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
            from_node[v] = [val + float(getattr(container, k)) for val in from_node[v]]
    def my_range(attribute):
        from_settings = _range(attribute)
        if attribute in mapping:
            from_settings['max_value'] = round(Decimal(from_node[mapping[attribute]][0]), 1)
        return from_settings
    return my_range

def capacity(node):
    if not node:
        return { 'capacity_cpu' : 0, 'capacity_memory': 0, 'capacity_gpu' : 0}
    else:
        return { 'capacity_cpu' : 2, 'capacity_memory': 2, 'capacity_gpu' : 2}
#    api = Cluster()
#    api.query_nodes_status(node_list=[node], reset=True)
#    api.query_pods_status(field=["spec.nodeName=",node], reset=True)
#    api.resources_summary()
#    from_node = api.get_data()
#    mapping = {
#        'cpurequest': 'avail_cpu',
#        'memoryrequest': 'avail_memory',
#        'gpurequest': 'avail_gpu',
#    }
#    if container.node == node and container.state in [ Container.ST_RUNNING, Container.ST_NEED_RESTART ]:
#        #FIXME: what if ST_STARTING, ST_STOPPING?
#        for k, v in mapping.items():
#            from_node[v] = [val + float(getattr(container, k)) for val in from_node[v]]
#    def my_range(attribute):
#        from_settings = _range(attribute)
#        if attribute in mapping:
#            from_settings['max_value'] = round(Decimal(from_node[mapping[attribute]][0]), 1)
#        return from_settings
#    return my_range

class myNumberInput(forms.NumberInput):
    template_name = 'widget_decimal.html'

class FormContainer(forms.ModelForm):
    class Meta:
        model = Container
        fields = [ 'node', 'cpurequest', 'gpurequest', 'memoryrequest', 'idletime' ]
    node = forms.ChoiceField(
        required = False,
        widget = forms.Select(attrs = tooltip_attrs({
            'title': _('Choose a node where to launch the environment.'), 
        }))
    )
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
    gpurequest = forms.IntegerField(
        label = 'GPU [#]', required = False,
        #**_range("gpurequest"),
        min_value = _range("gpurequest")['min_value'],
        widget = myNumberInput(attrs = tooltip_attrs({
            'title': _('Requested number of gpus for your container.'), 
        }))
    )
    memoryrequest = forms.DecimalField(
        label = 'Memory [GB]', required = False,
        #**_range("memoryrequest"),
        min_value = _range("memoryrequest")['min_value'],
        widget = myNumberInput(attrs = tooltip_attrs({
            'title': _('Requested memory for your container.'), 
            'step': 0.1
        }))
    )
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user = kwargs.get('initial', {}).get('user')
        if hasattr(user, 'profile') and user.profile.can_choosenode:
            api = Cluster()
            api.query_nodes_status()
            self.fields['node'].choices = [('', 'Any node will do')] + [ (x, x) for x in api.node_df['node'].values ]
        else:
            for att in ['node', 'cpurequest', 'memoryrequest', 'gpurequest' ]:
                self.fields[att].widget = forms.HiddenInput()

