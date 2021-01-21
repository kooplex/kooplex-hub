from django import forms
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
import django_tables2 as tables

from hub.models import ProjectServiceBinding

from django.db import models

class T_SERVICE(tables.Table):
    class SelectColumn(tables.Column):
        def render(self, record):
            template = f"""
<div class="form-check form-switch">
  <input class="form-check-input" type="checkbox" id="cb_svcid-{record.id}" name="service_ids" value="{record.id}" />
  <label class="form-check-label" for="cb_svid-{record.id}"> Create</label>
</div>
            """
            return format_html(template)
    id = SelectColumn(verbose_name = 'Template', orderable = False)

    class Meta:
        model = ProjectServiceBinding
        fields = ('id', 'service__name', 'service__state')
        sequence = ('id', 'service__name', 'service__state')
        attrs = {
                     "class": "table table-striped table-bordered",
                     "thead": { "class": "thead-dark table-sm" },
                     "td": { "style": "padding:.5ex" },
                     "th": { "style": "padding:.5ex", "class": "table-secondary" }
                    }


