from django.utils.html import format_html
import django_tables2 as tables

from hub.models import FSLibrary
from hub.models import FSLibraryServiceBinding 


def table_fslibrary(service):
    lookup = dict([ (b.fslibrary, b.id) for b in FSLibraryServiceBinding.objects.filter(service = service) ])
    class SelectColumn(tables.Column):
        def render(self, record):
            if record in lookup.keys():
                template = f"""
<div class="form-check form-switch">
  <input type="hidden" name="fslpb_ids_before" value="{lookup[record]}">
  <input class="form-check-input" type="checkbox" id="cb_fslpbid-{record.id}" name="fslpb_ids_after" value="{lookup[record]}" checked />
  <label class="form-check-label" for="cb_fslpbid-{record.id}"> Mounted</label>
</div>
                """
            else:
                template = f"""
<div class="form-check form-switch">
  <input class="form-check-input" type="checkbox" id="cb_fsl-{record.id}" name="fsl_ids" value="{record.id}" />
  <label class="form-check-label" for="cb_fsl-{record.id}"> Mount</label>
</div>
                """
            return format_html(template)
    sc = SelectColumn

    class ServiceColumn(tables.Column):
        def render(self, record):
            return format_html(", ".join([ s.name for s in record.services ]))

    class T_FSLIBRARY(tables.Table):
        id = sc(verbose_name = 'Mount', orderable = False)
        services = ServiceColumn(verbose_name = 'Bound to service', empty_values = (), orderable = False)

        class Meta:
            model = FSLibrary
            fields = ('id', 'library_name', 'services', 'syncing')
            sequence = ('id', 'library_name', 'syncing', 'services')
            attrs = {
                     "class": "table table-striped table-bordered",
                     "thead": { "class": "thead-dark table-sm" },
                     "td": { "style": "padding:.5ex" },
                     "th": { "style": "padding:.5ex", "class": "table-secondary" }
                    }

    return T_FSLIBRARY

class T_FSLIBRARY_SYNC(tables.Table):
    class BackendColumn(tables.Column):
        def render(self, record):
            svc = record.token.syncserver
            if svc.backend_type == svc.TP_SEAFILE:
                return format_html('<img src="/static/content/logos/seafile.png" alt="seafile" width="55px" data-toggle="tooltip" title="{}" data-placement="bottom">'.format(svc.url))
            else:
                return format_html(record)

    syncing = tables.Column(verbose_name = 'Status', orderable = False)
    backend_type = BackendColumn(verbose_name = 'Service', empty_values = (), orderable = False)
    service = tables.Column(verbose_name = 'Service environments', empty_values = (), orderable = False)
    sync_folder = tables.Column(verbose_name = 'Empty cache', empty_values = (), orderable = False)

    def render_syncing(self, record):
        if record.syncing:
            template = f"""
<div class="form-check form-switch">
  <input class="form-check-input" type="checkbox" id="cb_s-{record.id}" name="sync_library_id" value="{record.library_id}" checked />
  <label class="form-check-label" for="cb_s-{record.id}"> Keep synchronized</label>
</div>
            """
        elif record.sync_folder:
            template = f"""
<div class="form-check form-switch">
  <input class="form-check-input" type="checkbox" id="cb_s-{record.id}" name="sync_library_id" value="{record.library_id}" />
  <label class="form-check-label" for="cb_s-{record.id}"> Unpause</label>
</div>
            """
        else:
            template = f"""
<div class="form-check form-switch">
  <input class="form-check-input" type="checkbox" id="cb_s-{record.id}" name="sync_library_id" value="{record.library_id}" />
  <label class="form-check-label" for="cb_s-{record.id}"> Synchronize</label>
</div>
            """
        return format_html(template)

    def render_service(self, record):
        return format_html(', '.join([ s.name for s in record.services ]))

    def render_sync_folder(self, record):
        if record.sync_folder:
            template = f"""
<div class="form-check form-switch">
  <input class="form-check-input bg-danger" type="checkbox" id="cb_sf-{record.id}" name="dropcache_library_id" value="{record.library_id}" />
  <label class="form-check-label" for="cb_sf-{record.id}"> {record.sync_folder}</label>
</div>
            """
            return format_html(template)
        else:
            return format_html('-')

    class Meta:
        model = FSLibrary
        fields = ('library_name', 'syncing', 'backend_type', 'service', 'sync_folder')
        sequence = ('syncing', 'backend_type', 'library_name', 'service', 'sync_folder')
        attrs = {
                     "class": "table table-striped table-bordered",
                     "thead": { "class": "thead-dark table-sm" },
                     "td": { "style": "padding:.5ex" },
                     "th": { "style": "padding:.5ex", "class": "table-secondary" }
                    }

