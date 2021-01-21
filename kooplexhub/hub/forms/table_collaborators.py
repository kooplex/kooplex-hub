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
                template = f"""
<div class="form-check form-switch">
  <input type="hidden" name="collaborator_ids_before" value="{user.id}" />
  <input class="form-check-input" type="checkbox" id="cb_id-{user.id}" name="collaborator_ids_after" value="{user.id}" checked />
  <label class="form-check-label" for="cb_id-{user.id}"> Remove</label>
</div>
                """
            else:
                template = f"""
<div class="form-check form-switch">
  <input class="form-check-input" type="checkbox" id="cb_id-{user.id}" name="collaborator_ids_after" value="{user.id}" />
  <label class="form-check-label" for="cb_id-{user.id}"> Add</label>
</div>
                """
            return format_html(template)
    sc = SelectColumn

    class RoleColumn(tables.Column):
        def render(self, record):
            user = record.user
            if user in project.admins:
                template = f"""
<div class="form-check form-switch">
  <input type="hidden" name="admin_ids_before" value="{user.id}" />
  <input class="form-check-input" type="checkbox" id="cb_admid-{user.id}" name="admin_ids_after" value="{user.id}" checked />
  <label class="form-check-label" for="cb_admid-{user.id}"> Revoke</label>
</div>
                """
            else:
                template = f"""
<div class="form-check form-switch">
  <input class="form-check-input" type="checkbox" id="cb_admid-{user.id}" name="admin_ids_after" value="{user.id}" />
  <label class="form-check-label" for="cb_admid-{user.id}"> Grant</label>
</div>
                """
            return format_html(template)
    rc = RoleColumn

    class T_COLLABORATORS(tables.Table):
        id = SelectColumn(verbose_name = 'Collaboration', orderable = False)
        role = RoleColumn(verbose_name = 'Admin role', empty_values = (), orderable = False)
        name = tables.Column(order_by = ('user__first_name', 'user__last_name'))

        def render_name(self, record):
            user = record.user
            return format_html(f'<span data-toggle="tooltip" title="Username {user.username}." data-placement="top" style="font-weight: bold;">{user.first_name}</span> {user.last_name}')
    
        class Meta:
            model = Profile
            fields = ('id', 'role', 'name', 'location')
            sequence = ('id', 'role', 'name', 'location')
            attrs = {
                     "class": "table table-striped table-bordered",
                     "thead": { "class": "thead-dark table-sm" },
                     "td": { "style": "padding:.5ex" },
                     "th": { "style": "padding:.5ex", "class": "table-secondary" }
                    }


    return T_COLLABORATORS
