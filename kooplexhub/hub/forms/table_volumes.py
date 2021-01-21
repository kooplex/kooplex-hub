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
            attrs = {
                     "class": "table table-striped table-bordered",
                     "thead": { "class": "thead-dark table-sm" },
                     "td": { "style": "padding:.5ex" },
                     "th": { "style": "padding:.5ex", "class": "table-secondary" }
                    }
    return T_VOLUME(user_volumes)

def sel_col(project):
    class VolumeSelectionColumn(tables.Column):
        def render(self, record):
            if record in project.volumes:
                return format_html('<input type="checkbox" data-toggle="toggle" data-on="Unmount" data-off="Mounted" data-onstyle="danger" data-offstyle="success" data-size="xs" name="selection" value="%s">' % (record.id))
            else:
                return format_html('<input type="checkbox" data-toggle="toggle" data-on="Mount" data-off="Unmounted" data-onstyle="warning" data-offstyle="secondary" data-size="xs" name="selection" value="%s">' % (record.id))
    return VolumeSelectionColumn

class VolumePresentColumn(tables.Column):
        def render(self, record):
            if record.is_present:
               return format_html('<span class="true" data-toggle="tooltip" data-placement="top" title="Is present">✔</span>' )


def table_listvolume(user, volumetype):
    if volumetype == 'functional': #FIXME: Volume.FUNCTIONAL
        user_volumes = user.profile.functional_volumes
    elif volumetype == 'storage':
        user_volumes = user.profile.storage_volumes
#    column = sel_col(project)

    class T_VOLUME(tables.Table):
#        id = column(verbose_name = 'Selection')
        is_present = VolumePresentColumn(verbose_name = 'is present')

        class Meta:
            model = Volume
#            exclude = ('name', 'volumetype')
            attrs = {
                     "class": "table table-striped table-bordered",
                     "thead": { "class": "thead-dark table-sm" },
                     "td": { "style": "padding:.5ex" },
                     "th": { "style": "padding:.5ex", "class": "table-secondary" }
                    }
    return T_VOLUME(user_volumes)

class FormVolume(forms.ModelForm):
    volumetype = forms.ChoiceField(
            help_text = _('The volume type'),
            label= _('Type of volume')
        )

    class Meta:
        model = Volume
        fields = [ 'displayname', 'description', 'volumetype' ]
        labels = {
            'displayname': _('The name of your volume'),
            'description': _('A short description'),
            'volumetype': _('Type of volume'),
        }
        help_texts = {
            'displayname': _('Volume name should be unique.'),
            'description': _('It is always a good idea to have a short memo.'),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(FormVolume, self).__init__(*args, **kwargs)
        self.fields["volumetype"].choices = zip(Volume.VOLUME_TYPE_LIST_USER, Volume.VOLUME_TYPE_LIST_USER)
        for field in self.fields.keys():
            self.fields[field].widget.attrs["class"] = "form-control"

        for field in self.fields:
            help_text = self.fields[field].help_text
            self.fields[field].help_text = None
            if help_text != '':
                extra = {
                    'data-toggle': 'tooltip', 
                    'title': help_text,
                    'data-placement': 'bottom',
                }
                self.fields[field].widget.attrs.update(extra)
