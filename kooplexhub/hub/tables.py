#from django.utils.translation import gettext_lazy as _
from django.template.loader import render_to_string
import django_tables2 as tables

from django.contrib.auth.models import User

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
            'data-id': lambda record: record.pk
        }

    def __init__(self, users, marker_column=None):
        self.base_columns = self.base_columns.copy()
        if marker_column:
            self.base_columns[marker_column] = tables.Column(verbose_name = marker_column, orderable = False, empty_values = ())
            self.Meta.sequence = ('user', marker_column, 'remove',)
            setattr(self, f"render_{marker_column}", self.marked_render)
        super().__init__(users)
        self._initialize_columns()
        self.marker_column=marker_column
        #raise Exception(str(self.base_columns))

    def _initialize_columns(self):
        # Rebuild BoundColumns to ensure the new column is recognized
        from django_tables2.columns.base import BoundColumns
        self.sequence = self.Meta.sequence
        self.columns = tables.columns.BoundColumns(self, self.base_columns)

    def marked_render(self, value, record):
        return render_to_string("widgets/widget_toggler.html", {"pk": record.id, "mark": self.marker_column })

    def render_user(self, record):
        return record.profile.render_html()

    def render_remove(self, record):
        return render_to_string("widgets/widget_remove.html", {"pk": record.id, "remove": "user", "tooltip": "Remove user"}) #FIXME: 


