#from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
import django_tables2 as tables

from ..models import UserProjectBinding
from ..models import ProjectContainerBinding
from container.models import Container
from hub.models import Profile


class TableShowhideProject(tables.Table):
    button = tables.Column (verbose_name = 'Visible', orderable = False, empty_values = ())
    project = tables.Column (orderable = False)
    collaborators = tables.Column (orderable = False, empty_values = ())

    def render_button(self, record):
        state = "" if record.is_hidden else "checked"
        icon = "bi-eye-slash" if record.is_hidden else "bi-eye"
        return format_html(f"""
<input type="checkbox" class="btn-check" name="show" value="{record.id}" id="btn-{record.id}" autocomplete="off" {state}>
<label class="btn btn-outline-secondary" for="btn-{record.id}"><i class="bi {icon}"></i></label>
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


    class Meta:
        model = UserProjectBinding
        fields = ('project', )
        sequence = ('button', 'project', 'collaborators')
        attrs = { 
                 "class": "table table-bordered", 
                 "thead": { "class": "thead-dark table-sm" }, 
                 "th": { "class": "table-secondary" },
                }

    def __init__(self, *argv, **kwargs):
        self.user = kwargs.pop('user') if 'user' in kwargs else None
        super().__init__(*argv, **kwargs)


class TableJoinProject(tables.Table):
    class SelectColumn(tables.Column):
        def render(self, record):
            p = record.project
            template = f"""
<div class="form-check">
  <input class="form-check-input" type="checkbox" id="cb_pid-{p.id}" name="project_ids" value="{p.id}" />
  <label class="form-check-label" for="cb_pid-{p.id}"> Join</label>
</div>
            """
            return format_html(template)
    id = SelectColumn(verbose_name = 'Select', orderable = False)
    class UserColumn(tables.Column):
        def render(self, record):
            return format_html(record.user.profile.name_and_username)
    user = UserColumn(verbose_name = 'Creator name (username)', order_by = ('user__first_name', 'user__last_name'))
    class ImageColumn(tables.Column):
        def render(self, record):
            p = record.project
            images = set([ psb.container.image for psb in ProjectContainerBinding.objects.filter(project = p, container__user = p.creator) ])
            template = [ f"""
<div class="form-check">
  <input class="form-check-input" type="checkbox" id="cb_img_pid-{p.id}" name="image_ids" value="{i.id}" />
  <label class="form-check-label" for="cb_img_pid-{p.id}"> {i.name}</label>
</div>
            """ for i in images ]
            return format_html('<br>'.join(template))
    images = ImageColumn(verbose_name = 'Create environment', orderable = False, empty_values = ())
  
    class Meta:
        model = UserProjectBinding
        fields = ('id', 'project', 'user', 'images')
        sequence = ('id', 'project', 'user', 'images')
        attrs = {
                     "class": "table table-striped table-bordered",
                     "thead": { "class": "thead-dark table-sm" },
                     "td": { "style": "padding:.5ex" },
                     "th": { "style": "padding:.5ex", "class": "table-secondary" }
                    }
  
  
class TableCollaborator(tables.Table):
    user = tables.Column(verbose_name = "Collaborators", order_by = ('user__first_name', 'user__last_name'), orderable = False)
    #role = tables.Column(verbose_name = 'Admin role', empty_values = (), orderable = False)

    class Meta:
        model = UserProjectBinding
        fields = ('user',)
        attrs = {
                 "class": "table table-bordered",
                 "thead": { "class": "thead-dark table-sm" },
                 "td": { "class": "p-1" },
                 "th": { "class": "table-secondary p-1" }
                }

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


    def render_user(self, record):
        #FIXME: role
        user = record.user
        prefix = "" if self.is_collaborator_table else "_"
        hidden = f"""
<input type="hidden" name="{prefix}userprojectbinding_id" value="{record.id}">
        """ if record.id else f"""
<input type="hidden" name="{prefix}user_id" value="{record.user.id}">
        """
        return format_html(f"""
<span id="userid-{user.id}" data-toggle="tooltip" title="Username {user.username}." data-placement="top"><b>{user.first_name}</b> {user.last_name}</span>
<input type="hidden" id="search-collaborator-{user.id}" value="{user.username} {user.first_name} {user.last_name} {user.first_name}">
{hidden}
        """)


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
<input type="checkbox" class="btn-check" name="attach" value="{record.id}" id="btn-{record.id}" autocomplete="off" checked>
<label class="btn btn-outline-secondary" for="btn-{record.id}"><i class="bi bi-file-plus"></i></label>
            """)
        except ProjectContainerBinding.DoesNotExist:
            return format_html(f"""
<input type="checkbox" class="btn-check" name="attach" value="{record.id}" id="btn-{record.id}" autocomplete="off">
<label class="btn btn-outline-secondary" for="btn-{record.id}"><i class="bi bi-file-minus"></i></label>
        """)

    def render_b_project(self, record):
        return format_html(f"""
<input type="checkbox" class="btn-check" name="template" value="{record.id}" id="btn-{record.id}" autocomplete="off">
<label class="btn btn-outline-secondary" for="btn-{record.id}"><i class="bi bi-boxes"></i></label>
        """)

    def render_name(self, record):
        return format_html(f"""
<span data-toggle="tooltip" title="Container name: {record.name}." data-placement="bottom">{record.friendly_name}</span>
        """)


    def render_image(self, record):
        from container.templatetags.container_buttons import container_image
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
