from django import forms
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
import django_tables2 as tables

from hub.models import Profile
from hub.models import UserProjectBinding

def role_column(project):
    class RoleColumn(tables.Column):
        def render(self, record):
            try:
                role = UserProjectBinding.objects.get(user = record.user, project = project).role
            except UserProjectBinding.DoesNotExist:
                role = 'Skip'
            s0 = 'selected' if role == 'Skip' else role
            s1 = 'selected' if role == 'member' else role
            s2 = 'selected' if role == 'administrator' else role
            widget_str = """
<select name="role_map">
  <option value="skip-%d" %s>Skip/Remove</option>
  <option value="collaborator-%d" %s>Collaborator</option>
  <option value="admin-%d" %s>Administrator</option>
</select>
<input type='hidden' name='role_map_before' value='%s-%d'>
""" % (record.user.id, s0, record.user.id, s1, record.user.id, s2, role, record.user.id)
            return format_html(widget_str)
    return RoleColumn

from django.db import models

def table_collaboration(project):
    rc = role_column(project)
    class T_COLLABORATORS(tables.Table):
        id = rc(verbose_name = 'Role', orderable = False)
        name = tables.Column(order_by = ('user__first_name', 'user__last_name')) #FIXME: concatenate
        username = tables.Column(order_by = ('user__username'))
    
        class Meta:
            model = Profile
            fields = ('id', 'name', 'username', 'bio', 'location')
            sequence = ('id', 'name', 'username', 'location', 'bio')
            attrs = { "class": "table-striped table-bordered", "td": { "style": "padding:.5ex" } }

#        def order_name(self, QuerySet, is_descending):
#            QuerySet = QuerySet.annotate(
#                #FIXME: concat names
#            )#.order_by(('-' if is_descending else '') + 'name')
#            return (QuerySet, True)

    return T_COLLABORATORS
