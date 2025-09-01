#from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
import django_tables2 as tables

from .models import UserProjectBinding
from .models import ProjectContainerBinding
from container.models import Container
from django.contrib.auth.models import User
from hub.models import Profile

from container.templatetags.container_buttons import button_image
from hub.templatetags.extras import render_user as ru

from kooplexhub.common import table_attributes


class TableProject(tables.Table):
    button = tables.TemplateColumn(
        template_name="project/tables/project_attach_toggle.html",
        verbose_name="Attach",
        orderable=False,
        extra_context={"size": "small"}, 
    )

    project = tables.Column(
        verbose_name="Project",
        orderable=False,
    )

    collaborators = tables.TemplateColumn(
        template_name="project/tables/project_collaborators.html",
        verbose_name="Collaborators",
        orderable=False,
    )

    class Meta:
        model = UserProjectBinding
        fields = ("project",) 
        sequence = ("button", "project", "collaborators")
        attrs = table_attributes

    # ---- Factory
    @classmethod
    def from_user(cls, user, **kwargs):
        qs = (
            UserProjectBinding.objects
            .filter(user=user)
            .select_related("project")
            .prefetch_related("project__userbindings__user")
        )
        return cls(qs, **kwargs)
























class TableCollaborators(tables.Table):
    user=tables.Column(verbose_name = "User", order_by = ('scope', 'user__first_name', 'user__last_name'), orderable = False)
    username=tables.Column(verbose_name = "username", orderable = False, empty_values = ())
    role=tables.Column(verbose_name = "role", orderable = False, empty_values = ())
    class Meta:
        model = UserProjectBinding
        fields = ('user',)
        attrs = table_attributes

    def render_user(self, record):
        return record.user.profile.render_html()

    def render_username(self, record):
        return record.user.username

    def render_role(self, record):
        return record.role


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

#FIXME: check still used?
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
<span data-toggle="tooltip" title="Container name: {record.name}." data-placement="bottom">{record.name}</span>
        """)

    def render_image(self, record):
        return button_image(record)


    def __init__(self, user, project):
        containers = Container.objects.filter(user = user)
        self.project = project
        if project.id:
            UserProjectBinding.objects.get(user = user, project = project)
        super().__init__(containers)

