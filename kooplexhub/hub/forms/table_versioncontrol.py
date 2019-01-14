from django import forms
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
import django_tables2 as tables

from hub.models import VCProjectProjectBinding 
from hub.models import VCProject

def s_column(project):
    lookup = dict([ (b.vcproject, b.id) for b in VCProjectProjectBinding.objects.filter(project = project) ])
    class SelectColumn(tables.Column):
        def render(self, record):
            if record in lookup.keys():
                return format_html("<input type='hidden' name='vcppb_ids_before' value='%d'><input type='checkbox' name='vcppb_ids_after' value='%d' checked>" % (lookup[record], lookup[record]))
            else:
                return format_html("<input type='checkbox' name='vcp_ids' value='%d'>" % (record.id))
    return SelectColumn

class RepoColumn(tables.Column):
    def render(self, record):
        return format_html("%s/%s" % (record.token.url, record.project_name))

class ProjectsColumn(tables.Column):
    def render(self, record):
        return format_html(",".join(map(lambda b: str(b.project), record.vcprojectprojectbindings)))

def table_vcproject(project):
    sc = s_column(project)
    class T_VCPROJECT(tables.Table):
        id = sc(verbose_name = 'Select', orderable = False)
        repository = RepoColumn(verbose_name = 'Repository', empty_values = (), orderable = False) #FIXME: ordering (https://django-tables2.readthedocs.io/en/latest/pages/ordering.html)
        projects = ProjectsColumn(verbose_name = 'Bound to projects', empty_values = (), orderable = False)
        class Meta:
            model = VCProject
            fields = ('id', 'repository', 'projects')
            sequence = ('id', 'repository', 'projects')
            attrs = { "class": "table-striped table-bordered", "td": { "style": "padding:.5ex" } }

    return T_VCPROJECT
