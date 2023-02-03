#from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
import django_tables2 as tables

from ..models import UserProjectBinding
from ..models import ProjectContainerBinding
from container.models import Container
from hub.models import Profile

from container.templatetags.container_buttons import container_image
from hub.templatetags.extras import render_user as ru

from kooplexhub.common import table_attributes

class TableJoinProject(tables.Table):
    button = tables.Column (verbose_name = 'Join', orderable = False, empty_values = ())
    project = tables.Column (orderable = False)
    user = tables.Column(verbose_name = "Project owner", order_by = ('user__first_name', 'user__last_name'), orderable = False)
    collaborators = tables.Column(verbose_name = "Collaborators", orderable = False, empty_values = ())

    class Meta:
        model = UserProjectBinding
        fields = ('project', 'user', )
        sequence = ('button', 'project', 'user', 'collaborators')
        attrs = table_attributes

    def render_button(self, record):
        return format_html(f"""
<input id="btn-{record.id}" data-size="small"
     type="checkbox" data-toggle="toggle" name="join_project_ids"
     data-on="<span class=' bi bi-people'></span>"
     data-off="<span class='bi bi-people'></span>"
     data-onstyle="success" data-offstyle="secondary" value="{record.project.id}">
<input type="hidden" id="project-search-{record.project.id}" value="{record.project.search}">
<input type="hidden" id="project-match-{record.project.id}" value=true>
<input type="hidden" id="project-isshown-{record.project.id}" value=true>
        """)

    def render_project(self, record):
        return record.project.name

    def render_user(self, record):
        return ru(record.user)

    def render_collaborators(self, record):
        cols = UserProjectBinding.objects.filter(project = record.project).exclude(user = record.user)
        return format_html(', '.join([ ru(c.user) for c in cols ])) if cols else '--'


class TableCollaborator(tables.Table):
    user = tables.Column(verbose_name = "Collaborators", order_by = ('user__first_name', 'user__last_name'), orderable = False)

    class Meta:
        model = UserProjectBinding
        fields = ('user',)
        attrs = table_attributes

    def render_user(self, record):
        user = record.user
        prefix = "C" if self.is_collaborator_table else ""
        dhidden = "me-2" if self.is_collaborator_table else 'class="me-2 d-none"'
        chk = "checked" if self.is_collaborator_table and record.role == record.RL_ADMIN else ""
        o_adm = "opacity-75" if self.is_collaborator_table and record.role == record.RL_ADMIN else ""
        o_nadm = "" if self.is_collaborator_table and record.role == record.RL_ADMIN else "opacity-75"
        return format_html(f"""
<span id="admintoggler-{user.id}" {dhidden}><input id="admin-{user.id}" data-size="small"
  type="checkbox" data-toggle="toggle" name="{prefix}admin_id"
  data-on="<span class='oi oi-lock-unlocked'></span>"
  data-off="<span class='oi oi-lock-locked'></span>"
  data-onstyle="success {o_adm}" data-offstyle="danger {o_nadm}" {chk} value="{user.id}"></span>
{ru(user)}
<input type="hidden" id="{prefix}collaborator-search-{user.id}" value="{user.profile.search}">
<input type="hidden" id="{prefix}collaborator-match-{user.id}" value=true>
<input type="hidden" id="{prefix}collaborator-isshown-{user.id}" value=true>
        """)


    def __init__(self, project, user, collaborator_table):
        collaborators = UserProjectBinding.objects.filter(project = project)
        self.is_collaborator_table = collaborator_table
        if collaborator_table:
            bindings = collaborators.exclude(user = user)
        else:
            profiles = user.profile.everybodyelse.exclude(user__in = project.collaborators)
            bindings = [ UserProjectBinding(user = p.user, project = project) for p in profiles ]
        self.Meta.attrs["id"] = "collaborators" if collaborator_table else "users"
        super(TableCollaborator, self).__init__(bindings)


class TableContainer(tables.Table):
    image = tables.Column(orderable = False)
    name = tables.Column(verbose_name = 'Environment', orderable = False)
    button = tables.Column(verbose_name = 'Attach', orderable = False, empty_values = ())

    class Meta:
        model = Container
        fields = ('name', 'image')
        sequence = ('button', 'name', 'image')
        attrs = table_attributes

    def _hidden(self, record):
        return f"""
<input type="hidden" id="container-search-{record.id}" value="{record.search}">
<input type="hidden" id="container-match-{record.id}" value=true>
<input type="hidden" id="container-isshown-{record.id}" value=true>
        """

    def render_button(self, record):
        state = 'checked' if ProjectContainerBinding.objects.filter(project = self.project, container = record) else ''
        return format_html(f"""
<input id="containertoggler-{record.id}"
  type="checkbox" data-toggle="toggle" name="attach" data-size="small"
  data-on="<span class='bi bi-file-plus'></span>"
  data-off="<span class='bi bi-file-minus'></span>"
  data-onstyle="success opacity-75" data-offstyle="secondary" value="{record.id}" {state}></span>
{self._hidden(record)}
        """)

    def render_name(self, record):
        return format_html(f"""
<span data-toggle="tooltip" title="Container name: {record.name}." data-placement="bottom">{record.friendly_name}</span>
        """)

    def render_image(self, record):
        return container_image(record)


    def __init__(self, user, project):
        containers = Container.objects.filter(user = user)
        self.project = project
        if project.id:
            UserProjectBinding.objects.get(user = user, project = project)
        super().__init__(containers)

