from django import forms
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
import django_tables2 as tables

from hub.models import Volume
from hub.models import UserProjectBinding


from django.db import models

def table_volume(project, user, volumetype):
    if volumetype == 'functional': #FIXME: Volume.FUNCTIONAL
        user_volumes = user.profile.functional_volumes
    elif volumetype == 'storage':
        user_volumes = user.profile.storage_volumes
    column = sel_col(project)

    class T_VOLUME(tables.Table):
        id = column(verbose_name = 'Selection')
        is_present = VolumePresentColumn(verbose_name = 'is present')

        class Meta:
            model = Volume
            exclude = ('name', 'volumetype')
            attrs = { "class": "table-striped table-bordered", "style": "margin-left: 20px", "td": { "style": "padding:6px;" }, 
                    'th' : {"style":"display:none;"},
                    'tr' : {"style":"padding-bottom:15px;"},

                    }
    return T_VOLUME(user_volumes)

def sel_col(project):
    class VolumeSelectionColumn(tables.Column):
        def render(self, record):
            state = "checked" if record in project.volumes else ""
            return format_html('<input type="checkbox" data-toggle="toggle" data-on="Mounted" data-off="Unmounted" data-onstyle="danger" data-offstyle="success" data-size="xs" name="selection" value="%s">' % (record.id))
    return VolumeSelectionColumn

class VolumePresentColumn(tables.Column):
        def render(self, record):
            if record.is_present:
               return format_html('<span class="true" data-toggle="tooltip" data-placement="top" title="Is present">✔</span>' )


