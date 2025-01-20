#from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
import django_tables2 as tables

from django.contrib.auth.models import User

from hub.templatetags.extras import render_user as ru

from kooplexhub.common import table_attributes

_a = table_attributes.copy()
_a['class'] += " mt-2"

class TableUsers(tables.Table):
    user = tables.Column(verbose_name = "User", order_by = ('first_name', 'last_name'), orderable = False, empty_values = ())
    remove = tables.Column(verbose_name = "Remove", orderable = False, empty_values = ())

    class Meta:
        model = User
        fields = ()
        sequence = ('user', 'remove',)
        attrs = _a
        row_attrs = {
            'data-pk': lambda record: record.pk
        }

    def __init__(self, users, marker_column=None):
        self.base_columns = self.base_columns.copy()
        if marker_column:
            self.base_columns[marker_column] = tables.Column(verbose_name = marker_column, orderable = False, empty_values = ())
            self.Meta.sequence = ('user', marker_column, 'remove',)
        super().__init__(users)
        self._initialize_columns()
        self.marker_column=marker_column
        #raise Exception(str(self.base_columns))

    def _initialize_columns(self):
        # Rebuild BoundColumns to ensure the new column is recognized
        from django_tables2.columns.base import BoundColumns
        self.sequence = self.Meta.sequence
        self.columns = tables.columns.BoundColumns(self, self.base_columns)

#    def render_user(self, record):
#        return record.profile.render_html()
#
    def render(self, column, record):
        if column == getattr(self, 'marker_column', None):
            return format_html(f"""
<span id="admintoggler-{record.id}"><input data-size="small"
  type="checkbox" data-toggle="toggle" name="admin_id"
  data-on="<span class='oi oi-lock-unlocked'></span>"
  data-off="<span class='oi oi-lock-locked'></span>"
  data-pk="{record.pk}"
  data-onstyle="success" data-offstyle="danger" value="{record.id}"></span>
        """)
        return super().render(column, record)

#    def render_remove(self, record):
#        return format_html(f"""
#<button role="button" class="badge rounded-pill text-bg-danger border text-light p-2" onclick="UserSelection.removeUser({record.pk})"><span class="oi oi-minus" data-toggle="tooltip" title="Remove {record.first_name} {record.last_name} from collaboration" data-placement="top"></span></button>
#        """)


