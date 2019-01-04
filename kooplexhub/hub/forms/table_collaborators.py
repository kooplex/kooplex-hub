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
</select> %s
""" % (record.user.id, s0, record.user.id, s1, record.user.id, s2, role)
            return format_html(widget_str)
    return RoleColumn

class NameColumn(tables.Column):
    def render(self, record):
        u = record.user
        return format_html("%s %s (%s)" % (u.first_name, u.last_name, u.username))


def table_collaboration(project):
    rc = role_column(project)
    class T_COLLABORATORS(tables.Table):
        id = rc(verbose_name = 'Role', orderable = False)
        user = NameColumn(verbose_name = 'Name', orderable = False)
    
        class Meta:
            model = Profile
            fields = ('id', 'user', 'bio', 'location')
            sequence = ('id', 'user', 'location', 'bio')
            attrs = { "class": "table-striped table-bordered", "td": { "style": "padding:.5ex" } }

    return T_COLLABORATORS
