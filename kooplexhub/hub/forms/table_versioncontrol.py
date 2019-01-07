from django import forms
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
import django_tables2 as tables

from hub.models import VCProjectProjectBinding 

class SelectColumn(tables.Column):
    def render(self, record):
        vcp = record.vcproject
        if record.id is None:
            return format_html("<input type='checkbox' name='vcp_ids' value='%d'>" % (vcp.id))
        else:
            return format_html("<input type='checkbox' name='vcppb_ids' value='%d' checked>" % (record.id))

class VCProjectColumn(tables.Column):
    def render(self, record):
        p = record.vcproject
        return format_html("%s/%s" % (p.token.url, p.project_name))

class OtherProjectsColumn(tables.Column):
    def render(self, value):
        return format_html(",".join(map(lambda x: str(x), value)))

class T_PROJECTPROJECTMAP(tables.Table):
    id = SelectColumn(verbose_name = 'Select', orderable = False, empty_values = ())
    vcproject = VCProjectColumn(verbose_name = 'Repository', orderable = False)
    otherprojects = OtherProjectsColumn(verbose_name = 'Bound to projects', orderable = False)
    class Meta:
        model = VCProjectProjectBinding
        fields = ('id', 'vcproject', 'otherprojects')
#        sequence = ('id', 'project', 'user')
        attrs = { "class": "table-striped table-bordered", "td": { "style": "padding:.5ex" } }
