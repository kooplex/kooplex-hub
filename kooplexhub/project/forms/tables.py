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
        return format_html(f"""
<input type="hidden" name="search" value="{record.project.name}">{record.project.name}
        """)

    def render_collaborators(self, record):
        collaborators = record.project.collaborators
        collaborators.remove(self.user)
        ru = lambda u: f"{u.first_name} {u.last_name}"
        return ", ".join([ ru(u) for u in collaborators ]) if len(collaborators) else ""


    class Meta:
        model = UserProjectBinding
        fields = ('project', )
        sequence = ('button', 'project', 'collaborators')
        attrs = { 
                 "class": "table table-bordered", 
                 "thead": { "class": "thead-dark table-sm" }, 
                 #"td": { "class": "w-100" }, 
                 "th": { "class": "table-secondary" },
                 #"tr": { "class": "w-100" },
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
    user = tables.Column(verbose_name = "Collaborators", order_by = ('user__first_name', 'user__last_name'))
    #role = tables.Column(verbose_name = 'Admin role', empty_values = (), orderable = False)

    class Meta:
        model = UserProjectBinding
        fields = ('user',)
        attrs = {
                 "class": "table table-striped table-bordered",
                 "thead": { "class": "thead-dark table-sm" },
                 "td": { "style": "padding:.5ex" },
                 "th": { "style": "padding:.5ex", "class": "table-secondary" }
                }

    def __init__(self, project, user, collaborator_table):
        collaborators = UserProjectBinding.objects.filter(project = project)
        if collaborator_table:
            bindings = collaborators.exclude(user = user)
        else:
            profiles = user.profile.everybodyelse.exclude(user__in = project.collaborators)
            bindings = [ UserProjectBinding(user = p.user, project = project) for p in profiles ]
        self.Meta.attrs["id"] = "collaborators" if collaborator_table else "users"
        super(TableCollaborator, self).__init__(bindings)


    def render_user(self, record):
        user = record.user
        if record.id:
            return format_html(f"""
<span id="userid-{user.id}" data-toggle="tooltip" title="Username {user.username}." data-placement="top" style="font-weight: bold;">{user.first_name}</span> {user.last_name}
<input type="hidden" name="userprojectbinding_id" value="{record.id}">
            """)
        else:
            return format_html(f"""
<span id="userid-{user.id}" data-toggle="tooltip" title="Username {user.username}." data-placement="top" style="font-weight: bold;">{user.first_name}</span> {user.last_name}
<input type="hidden" id="search-collaborator-{user.id}" value="{user.username} {user.first_name} {user.last_name} {user.first_name}">
<input type="hidden" name="user_id" value="{record.user.id}">
            """)


    def render_role(self, record):
        return "alma"
        user = record.user
        return format_html()
#            template = f"""
# <div class="container" style="width: 170px">
#                  <div class="row" style="width: 170px">
#                    <div class="col-sm"><span>Grant</span></div>
#<div class="form-check col-sm form-switch">
#  <input class="form-check-input" type="checkbox" id="cb_admid-{user.id}" name="admin_ids_after" value="{user.id}" checked />
#  <label class="form-check-label" for="cb_admid-{user.id}"> Revoke</label>
#</div>
#</div>
#</div>
#            """
#        else:
#            template = f"""
#                          <div class="container" style="width: 170px">
#                  <div class="row" style="width: 170px">
#                    <div class="col-sm"><span>Grant</span></div>
#<div class="form-check col-sm form-switch">
#  <input class="form-check-input" type="checkbox" id="cb_admid-{user.id}" name="admin_ids_after" value="{user.id}" />
#  <label class="form-check-label" for="cb_admid-{user.id}"> Revoke</label>
#</div>
#</div>
#</div>
#            """



class TableProjectContainer(tables.Table):
    id = tables.Column(verbose_name = 'Template', orderable = False)

    class Meta:
        model = ProjectContainerBinding
        fields = ('id', 'container__name', 'container__state')
        attrs = {
                     "class": "table table-striped table-bordered",
                     "thead": { "class": "thead-dark table-sm" },
                     "td": { "style": "padding:.5ex" },
                     "th": { "style": "padding:.5ex", "class": "table-secondary" }
                    }

    def render_id(self, record):
        template = f"""
<div class="form-check">
  <input class="form-check-input" type="checkbox" id="cb_svcid-{record.id}" name="service_ids" value="{record.id}" />
  <label class="form-check-label" for="cb_svid-{record.id}"> Create</label>
</div>
        """
        return format_html(template)


class TableContainer(tables.Table):
    id = tables.Column(verbose_name = 'Environment', orderable = False)

    class Meta:
        model = Container
        fields = ('id', 'name', 'image', 'state')
        sequence = ('id', 'name', 'image', 'state')
        attrs = { 
                 "class": "table table-striped table-bordered", 
                 "thead": { "class": "thead-dark table-sm" }, 
                 "td": { "style": "padding:.5ex" }, 
                 "th": { "style": "padding:.5ex", "class": "table-secondary" } 
                }

    def __init__(self, userprojectbinding, containers):
        super(TableContainer, self).__init__(containers)
        self.upb = userprojectbinding

    def render_id(self, record):
        stl_add = 'danger' if record.state in [ record.ST_RUNNING, record.ST_NEED_RESTART ] else 'success'
        stl_rem = 'danger' if record.state in [ record.ST_RUNNING, record.ST_NEED_RESTART ] else 'dark'
        try:
            psb = ProjectContainerBinding.objects.get(project = self.upb.project, container = record)
            template = f"""
<div class="form-check form-switch">
  <input type="hidden" name="psb_ids_before" value="{psb.id}">
  <input class="form-check-input" type="checkbox" id="cb_psbid-{psb.id}" name="psb_ids_after" value="{psb.id}" checked />
  <label class="form-check-label" for="cb_psbid-{psb.id}"> Keep added</label>
</div>
            """
        except ProjectContainerBinding.DoesNotExist:
            template = f"""
<div class="form-check form-switch">
  <input class="form-check-input" type="checkbox" id="cb_svc-{record.id}" name="svc_ids" value="{record.id}" />
  <label class="form-check-label" for="cb_svcid-{record.id}"> Attach</label>
</div>
            """
        return format_html(template)


#FIXME:  from hub.models import Service
#FIXME:  
#FIXME:  def image_column(service):
#FIXME:      class ImageColumn(tables.Column):
#FIXME:          def render(self, record):
#FIXME:              image = record.project.image
#FIXME:              return format_html(str(image)) if image == service.image else format_html("<strong>%s</strong>" % image)
#FIXME:      return ImageColumn
#FIXME:  
#FIXME:  class CollaboratorColumn(tables.Column):
#FIXME:      def render(self, record):
#FIXME:          return format_html(', '.join(record.collaborators))
#FIXME:  
#FIXME:  

 
