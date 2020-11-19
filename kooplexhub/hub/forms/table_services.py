from django import forms
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
import django_tables2 as tables

from hub.models import ProjectServiceBinding

from django.db import models

class T_SERVICE(tables.Table):
    class SelectColumn(tables.Column):
        def render(self, record):
            return format_html('<input type="checkbox" name="service_ids" value="{0}" data-toggle="toggle" data-on="Copy" data-off="Skip" data-onstyle="success" data-offstyle="dark" data-size="xs">'.format(record.id))
    id = SelectColumn(verbose_name = 'Associate', orderable = False)

    class Meta:
        model = ProjectServiceBinding
        fields = ('id', 'service__name', 'service__state')
        sequence = ('id', 'service__name', 'service__state')
        attrs = { "class": "table table-striped table-bordered", "thead": { "class": "thead-dark table-sm" }, "td": { "style": "padding:.5ex" } }


