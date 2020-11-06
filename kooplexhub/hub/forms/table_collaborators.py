from django import forms
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
import django_tables2 as tables

from hub.models import Profile
from hub.models import UserProjectBinding


from django.db import models

def table_collaboration(project):
    class SelectColumn(tables.Column):
        def render(self, record):
            user = record.user
            if user in project.collaborators:
                return format_html('<input type="hidden" name="collaborator_ids_before" value="{0}"><input type="checkbox" name="collaborator_ids_after" value="{0}" checked data-toggle="toggle" data-on="Keep added" data-off="Remove" data-onstyle="success" data-offstyle="dark" data-size="xs" checked>'.format(user.id))
            else:
                return format_html('<input type="checkbox" name="collaborator_ids_after" data-toggle="toggle" value="{}" data-on="Add" data-off="Skip" data-onstyle="success" data-offstyle="dark" data-size="xs">'.format(record.id))
    sc = SelectColumn

    class RoleColumn(tables.Column):
        def render(self, record):
            user = record.user
            if user in project.admins:
                return format_html('<input type="hidden" name="admin_ids_before" value="{0}"><input type="checkbox" name="admin_ids_after" value="{0}" checked data-toggle="toggle" data-on="Admin" data-off="Collaborator" data-onstyle="danger" data-offstyle="success" data-size="xs" checked>'.format(user.id))
            else:
                return format_html('<input type="checkbox" name="admin_ids_after" data-toggle="toggle" value="{}" data-on="Admin" data-off="Collaborator" data-onstyle="danger" data-offstyle="success" data-size="xs">'.format(record.id))
    rc = RoleColumn

    class T_COLLABORATORS(tables.Table):
        id = SelectColumn(verbose_name = 'Associate', orderable = False)
        role = RoleColumn(verbose_name = 'Role', empty_values = (), orderable = False)
        name = tables.Column(order_by = ('user__first_name', 'user__last_name'))

        def render_name(self, record):
            user = record.user
            return format_html(f'<span data-toggle="tooltip" title="Username {user.username}." data-placement="top" style="font-weight: bold;">{user.first_name}</span> {user.last_name}')
    
        class Meta:
            model = Profile
            fields = ('id', 'role' 'name', 'location')
            sequence = ('id', 'role', 'name', 'location')
            attrs = { "class": "table-striped table-bordered", "td": { "style": "padding:.5ex" } }

    return T_COLLABORATORS
