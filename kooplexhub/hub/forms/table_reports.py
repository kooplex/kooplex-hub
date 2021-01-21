from django import forms
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
import django_tables2 as tables

from hub.models import Report


class T_REPORTS(tables.Table):
    openreport = tables.Column(verbose_name = 'Open', empty_values = ())

    def render_openreport(self, record):
        return format_html("""
<a href="%s" target="_blank" role="button" class="btn btn-info" style="min-width: 3em; text-align: left;"  title="Open this version"><span class="oi oi-external-link" aria-hidden="true"></span></a>
        """ % reverse('report:openreport', kwargs = {'report_id': record.id}))

    class Meta:
        model = Report
        orderable = False
        fields = ('openreport', 'created_at', 'tag_name')
        exclude = ('id', 'creator', 'name')
        attrs = {
                     "class": "table table-striped table-bordered",
                     "thead": { "class": "thead-dark table-sm" },
                     "td": { "style": "padding:.5ex" },
                     "th": { "style": "padding:.5ex", "class": "table-secondary" }
                    }


class T_REPORTS_DEL(T_REPORTS):
    deletereport = tables.Column(verbose_name = 'Delete', empty_values = ())

    def render_deletereport(self, record):
        return format_html("""
<a href="%s" role="button" class="btn btn-danger" style="text-align: left;"><span class="oi oi-trash" aria-hidden="true"></span></a>
        """ % reverse('report:deletereport', kwargs = {'report_id': record.id}))

    class Meta:
        model = Report
        orderable = False
        fields = ('openreport', 'deletereport', 'created_at', 'tag_name')
        exclude = ('id', 'creator', 'name')
        attrs = {
                     "class": "table table-striped table-bordered",
                     "thead": { "class": "thead-dark table-sm" },
                     "td": { "style": "padding:.5ex" },
                     "th": { "style": "padding:.5ex", "class": "table-secondary" }
                    }

