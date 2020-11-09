from django.utils.html import format_html
import django_tables2 as tables

from hub.models import FSLibrary
from hub.models import FSLibraryServiceBinding 


def table_fslibrary(service):
    lookup = dict([ (b.fslibrary, b.id) for b in FSLibraryServiceBinding.objects.filter(service = service) ])
    class SelectColumn(tables.Column):
        def render(self, record):
            if record in lookup.keys():
                #FIXME: name also in the template!!
                return format_html('<input type="hidden" name="fslpb_ids_before" value="{0}"><input type="checkbox" name="fslpb_ids_after" value="{0}" checked data-toggle="toggle" data-on="Attached" data-off="Detach" data-onstyle="success" data-offstyle="dark" data-size="xs">'.format(lookup[record]))
            else:
                return format_html('<input type="checkbox" name="fsl_ids" data-toggle="toggle" value="{}" data-on="Attach" data-off="Unused" data-onstyle="success" data-offstyle="dark" data-size="xs">'.format(record.id))
    sc = SelectColumn

    class ServiceColumn(tables.Column):
        def render(self, record):
            return format_html(", ".join([ s.name for s in record.services ]))

    class T_FSLIBRARY(tables.Table):
        id = sc(verbose_name = 'Status', orderable = False)
        services = ServiceColumn(verbose_name = 'Bound to service', empty_values = (), orderable = False)

        class Meta:
            model = FSLibrary
            fields = ('id', 'library_name', 'services', 'syncing')
            sequence = ('id', 'library_name', 'syncing', 'services')
            attrs = { "class": "table-striped table-bordered", "td": { "style": "padding:.5ex" } }

    return T_FSLIBRARY

class T_FSLIBRARY_SYNC(tables.Table):
    syncing = tables.Column(verbose_name = 'Status', orderable = False)
    class BackendColumn(tables.Column):
        def render(self, record):
            svc = record.token.syncserver
            if svc.backend_type == svc.TP_SEAFILE:
                return format_html('<img src="/static/content/logos/seafile.png" alt="seafile" width="55px" data-toggle="tooltip" title="{}" data-placement="bottom">'.format(svc.url))
            else:
                return format_html(record)
    backend_type = BackendColumn(verbose_name = 'Service', empty_values = (), orderable = False)
    service = tables.Column(verbose_name = 'Service environments', empty_values = (), orderable = False)

    def render_syncing(self, record):
        if record.syncing:
            return format_html('<input type="checkbox" data-toggle="toggle" name="sync_library_id" value="{}" data-on="Synchronizing" data-off="Pause" data-onstyle="success" data-offstyle="dark" data-size="xs" checked>'.format(record.library_id))
        elif record.sync_folder:
            return format_html('<input type="checkbox" data-toggle="toggle" name="sync_library_id" value="{}" data-on="Synchronize" data-off="Pause" data-onstyle="success" data-offstyle="dark" data-size="xs">'.format(record.library_id))
        else:
            return format_html('<input type="checkbox" data-toggle="toggle" name="sync_library_id" value="{}" data-on="Synchronize" data-off="Unused" data-onstyle="success" data-offstyle="secondary" data-size="xs">'.format(record.library_id))

    def render_service(self, record):
        return format_html(', '.join([ s.name for s in record.services ]))

    class Meta:
        model = FSLibrary
        fields = ('library_name', 'syncing', 'backend_type', 'service', 'sync_folder')
        sequence = ('syncing', 'backend_type', 'library_name', 'service', 'sync_folder')
        attrs = { "class": "table-striped table-bordered", "td": { "style": "padding:.5ex" } }

