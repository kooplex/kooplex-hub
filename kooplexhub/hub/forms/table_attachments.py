from django.utils.html import format_html
import django_tables2 as tables

from hub.models import Attachment
from hub.models import AttachmentServiceBinding 


def table_attachments(service):
    lookup = dict([ (b.attachment, b.id) for b in AttachmentServiceBinding.objects.filter(service = service) ])
    class SelectColumn(tables.Column):
        def render(self, record):
            if record in lookup.keys():
                template = f"""
<div class="form-check form-switch">
  <input type="hidden" name="asb_ids_before" value="{lookup[record]}">
  <input class="form-check-input" type="checkbox" id="cb_asbid-{record.id}" name="asb_ids_after" value="{lookup[record]}" checked />
  <label class="form-check-label" for="cb_asbid-{record.id}"> Mounted</label>
</div>
                """
            else:
                template = f"""
<div class="form-check form-switch">
  <input class="form-check-input" type="checkbox" id="cb_a-{record.id}" name="a_ids" value="{record.id}" />
  <label class="form-check-label" for="cb_a-{record.id}"> Mount</label>
</div>
                """
            return format_html(template)
    sc = SelectColumn


    class T_ATTACHMENT(tables.Table):
        id = sc(verbose_name = 'Mount', orderable = False)

        class Meta:
            model = Attachment
            fields = ('id', 'name', 'folder', 'description')
            sequence = ('id', 'name', 'folder', 'description')
            attrs = {
                     "class": "table table-striped table-bordered",
                     "thead": { "class": "thead-dark table-sm" },
                     "td": { "style": "padding:.5ex" },
                     "th": { "style": "padding:.5ex", "class": "table-secondary" }
                    }

    return T_ATTACHMENT

