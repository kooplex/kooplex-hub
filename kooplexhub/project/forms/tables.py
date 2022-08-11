#from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
import django_tables2 as tables

from ..models import UserProjectBinding
from ..models import ProjectContainerBinding
from container.models import Container
from hub.models import Profile

from container.templatetags.container_buttons import container_image
from hub.templatetags.extras import render_user as ru


class TableShowhideProject(tables.Table):
    button = tables.Column (verbose_name = 'Visible', orderable = False, empty_values = ())
    project = tables.Column (orderable = False)
    collaborators = tables.Column (orderable = False, empty_values = ())

    class Meta:
        model = UserProjectBinding
        fields = ('project', )
        sequence = ('button', 'project', 'collaborators')
        attrs = {
                 "class": "table table-bordered",
                 "thead": { "class": "thead-dark table-sm" },
                 "th": { "class": "table-secondary" },
                }

    def render_button(self, record):
        state = "" if record.is_hidden else "checked"
        o_hide = "opacity-75" if record.is_hidden else ""
        o_show = "" if record.is_hidden else "opacity-75"
        return format_html(f"""
<input id="btn-{record.id}" data-size="small"
     type="checkbox" data-toggle="toggle" name="show"
     data-on="<span class=' bi bi-eye'></span>"
     data-off="<span class='bi bi-eye-slash'></span>"
     data-onstyle="success {o_show}" data-offstyle="secondary {o_hide}" value="{record.id}" {state}>
        """)

    def render_project(self, record):
        return record.project.name

    def render_collaborators(self, record):
        collaborators = record.project.collaborators
        collaborators.remove(self.user)
        ru = lambda u: f"{u.first_name} {u.last_name}"
        collablist = list(map(ru, collaborators))
        collab_search = " ".join(collablist)
        collab_list = ", ".join(collablist)
        return format_html(f"""
<input type="hidden" name="search" value="{record.project.name} {collab_search}">{collab_list}
        """)


    def __init__(self, *argv, **kwargs):
        self.user = kwargs.pop('user') if 'user' in kwargs else None
        super().__init__(*argv, **kwargs)


class TableJoinProject(tables.Table):
    button = tables.Column (verbose_name = 'Join', orderable = False, empty_values = ())
    images = tables.Column (verbose_name = 'Image', orderable = False, empty_values = ())
    project = tables.Column (orderable = False)
    user = tables.Column(verbose_name = "Project owner", order_by = ('user__first_name', 'user__last_name'), orderable = False)
    collaborators = tables.Column(verbose_name = "Collaborators", orderable = False, empty_values = ())

    class Meta:
        model = UserProjectBinding
        fields = ('project', 'user', )
        sequence = ('button', 'project', 'user', 'collaborators', 'images')
        attrs = {
                     "class": "table table-striped table-bordered",
                     "thead": { "class": "thead-dark table-sm" },
                     "td": { "style": "padding:.5ex" },
                     "th": { "style": "padding:.5ex", "class": "table-secondary" }
                    }

    def render_button(self, record):
        return format_html(f"""
<input id="btn-{record.id}" data-size="small"
     type="checkbox" data-toggle="toggle" name="join_project_ids"
     data-on="<span class=' bi bi-people'></span>"
     data-off="<span class='bi bi-people'></span>"
     data-onstyle="success" data-offstyle="secondary" value="{record.project.id}">
        """)

    def render_images(self, record):
        p = record.project
        lut = { psb.container.id: container_image(psb.container) for psb in ProjectContainerBinding.objects.filter(project = p, container__user = p.creator) }
        template = [ f"""
<div class="form-check m-0">
  <input class="form-check-input" type="checkbox" id="container_template-{i}" name="container_template_ids-{p.id}" value="{i}">
  <label class="form-check-label" for="container_template-{i}">&nbsp;{c}</label>
</div>
        """ for i, c in lut.items() ]
        return format_html('<br>'.join(template))

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
        attrs = {
                 "class": "table table-bordered",
                 "thead": { "class": "thead-dark table-sm" },
                 "td": { "class": "p-1" },
                 "th": { "class": "table-secondary p-1" }
                }

    def render_user(self, record):
        user = record.user
        prefix = "" if self.is_collaborator_table else "_"
        hidden = f"""
<input type="hidden" name="{prefix}userprojectbinding_id" value="{record.id}">
        """ if record.id else f"""
<input type="hidden" name="{prefix}user_id" value="{record.user.id}">
        """
        dhidden = "" if self.is_collaborator_table else 'class="d-none"'
        chk = "checked" if self.is_collaborator_table and record.role == record.RL_ADMIN else ""
        o_adm = "opacity-75" if self.is_collaborator_table and record.role == record.RL_ADMIN else ""
        o_nadm = "" if self.is_collaborator_table and record.role == record.RL_ADMIN else "opacity-75"
        return format_html(f"""
<span id="d-{user.id}" {dhidden}><input id="admin-{user.id}" data-size="small"
  type="checkbox" data-toggle="toggle" name="{prefix}admin_id"
  data-on="<span class='oi oi-lock-unlocked'></span>"
  data-off="<span class='oi oi-lock-locked'></span>"
  data-onstyle="success {o_adm}" data-offstyle="danger {o_nadm}" {chk} value="{user.id}"></span>
{ru(user)}
<input type="hidden" id="search-collaborator-{user.id}" value="{user.username} {user.first_name} {user.last_name} {user.first_name}">
{hidden}
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
        attrs = {
                 "class": "table table-striped table-bordered",
                 "thead": { "class": "thead-dark table-sm" },
                 "td": { "class": "p-1" },
                 "th": { "class": "table-secondary p-1" }
                }

    def render_b_user(self, record):
        try:
            psb = ProjectContainerBinding.objects.get(project = self.upb.project, container = record)
            return format_html(f"""
<input id="btn-{record.id}"
  type="checkbox" data-toggle="toggle" name="attach" data-size="small"
  data-on="<span class='bi bi-file-plus'></span>"
  data-off="<span class='bi bi-file-minus'></span>"
  data-onstyle="success opacity-75" data-offstyle="secondary" value="{record.id}" checked></span>
            """)
        except ProjectContainerBinding.DoesNotExist:
            return format_html(f"""
<input id="btn-{record.id}"
  type="checkbox" data-toggle="toggle" name="attach" data-size="small"
  data-on="<span class='bi bi-file-plus'></span>"
  data-off="<span class='bi bi-file-minus'></span>"
  data-onstyle="success" data-offstyle="secondary opacity-75" value="{record.id}"></span>
        """)

    def render_b_project(self, record):
        return format_html(f"""
<input id="btn-{record.id}"
  type="checkbox" data-toggle="toggle" name="template" data-size="small"
  data-on="<span class='bi bi-boxes'></span>"
  data-off="<span class='bi bi-boxes'></span>"
  data-onstyle="success" data-offstyle="secondary opacity-75" value="{record.id}"></span>
        """)

    def render_name(self, record):
        return format_html(f"""
<span data-toggle="tooltip" title="Container name: {record.name}." data-placement="bottom">{record.friendly_name}</span>
        """)

    def render_image(self, record):
        return container_image(record)


    def __init__(self, user, project, axis):
        assert axis in [ 'user', 'project' ]
        if axis == 'user':
            containers = Container.objects.filter(user = user)
            self.render_button = self.render_b_user
            self.upb = UserProjectBinding.objects.get(user = user, project = project)
        else:
            containers = [ b.container for b in ProjectContainerBinding.objects.filter(project = project, container__user = user) ]
            self.render_button = self.render_b_project
        super().__init__(containers)

