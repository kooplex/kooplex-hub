from django.utils.html import format_html
import django_tables2 as tables

from hub.models import FSLibrary
from hub.models import FSLibraryProjectBinding 


def s_column(project):
    lookup = dict([ (b.fslibrary, b.id) for b in FSLibraryProjectBinding.objects.filter(project = project) ])
    class SelectColumn(tables.Column):
        def render(self, record):
            if record in lookup.keys():
                return format_html('<input type="hidden" name="fslpb_ids_before" value="{0}"><input type="checkbox" name="fslpb_ids_after" value="{0}" checked data-toggle="toggle" data-on="Attached" data-off="Detach" data-onstyle="success" data-offstyle="dark" data-size="xs">'.format(lookup[record]))
            else:
                return format_html('<input type="checkbox" name="fsl_ids" data-toggle="toggle" value="{}" data-on="Attach" data-off="Unused" data-onstyle="success" data-offstyle="dark" data-size="xs">'.format(record.id))
    return SelectColumn

class ProjectsColumn(tables.Column):
    def render(self, record):
        return format_html(",".join(map(lambda b: str(b.project), record.fslibraryprojectbindings)))


def table_fslibrary(project):
    sc = s_column(project)
    class T_FSLIBRARY(tables.Table):
        id = sc(verbose_name = 'Status', orderable = False)
        projects = ProjectsColumn(verbose_name = 'Bound to projects', empty_values = (), orderable = False)

        class Meta:
            model = FSLibrary
            fields = ('id', 'library_name', 'projects')
            sequence = ('id', 'library_name', 'projects')
            attrs = { "class": "table-striped table-bordered", "td": { "style": "padding:.5ex" } }

    return T_FSLIBRARY

class T_FSLIBRARY_SYNC(tables.Table):
    syncing = tables.Column(verbose_name = 'Status', orderable = False)
    def render_syncing(self, record):
        if record.syncing:
            return format_html('<input type="checkbox" data-toggle="toggle" name="sync_library_id" value="{}" data-on="Synchronizing" data-off="Pause" data-onstyle="success" data-offstyle="dark" data-size="xs" checked>'.format(record.library_id))
        elif record.sync_folder:
            return format_html('<input type="checkbox" data-toggle="toggle" name="sync_library_id" value="{}" data-on="Synchronize" data-off="Pause" data-onstyle="success" data-offstyle="dark" data-size="xs">'.format(record.library_id))
        else:
            return format_html('<input type="checkbox" data-toggle="toggle" name="sync_library_id" value="{}" data-on="Synchronize" data-off="Unused" data-onstyle="success" data-offstyle="secondary" data-size="xs">'.format(record.library_id))
    class Meta:
        model = FSLibrary
        fields = ('library_name', 'syncing')
        sequence = ('syncing', 'library_name')
        attrs = { "class": "table-striped table-bordered", "td": { "style": "padding:.5ex" } }

