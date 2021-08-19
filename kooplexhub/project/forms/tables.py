#from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
import django_tables2 as tables

from ..models import UserProjectBinding
from ..models import ProjectContainerBinding
from container.models import Container
from hub.models import Profile

class TableShowhideProject(tables.Table):
    #TODO: jQuery to change label
    class ProjectSelectionColumn(tables.Column):
        def render(self, record):
            if record.is_hidden:
                template = f"""
<div class="form-check form-switch">
  <input class="form-check-input" type="checkbox" id="cb_vpid-{record.id}" name="selection" value="{record.id}" checked />
  <label class="form-check-label" for="cb_vpid-{record.id} id="lbl_vpid-{record.id}"> Hidden</label>
</div>
                """
#$("#cb_vpid-{record.id}").on("change", function () {
#    if ($(this).is(":checked")) {
#        $('#cb_vpid-{record.id}').text("Hidden")
#    } else {
#        $('#lblauto').text("Show")
#    }
#})
            else:
                template = f"""
<div class="form-check form-switch">
  <input class="form-check-input" type="checkbox" id="cb_vpid-{record.id}" name="selection" value="{record.id}" />
  <label class="form-check-label" for="cb_vpid-{record.id} id="lbl_vpid-{record.id}"> Shown</label>
</div>
                """
#$("#cb_vpid-{record.id}").on("change", function () {
#    if ($(this).is(":checked")) {
#        $('#cb_vpid-{record.id}').text("Hide")
#    } else {
#        $('#lblauto').text("Shown")
#    }
#})
            return format_html(template)
    id = ProjectSelectionColumn(verbose_name = 'Visibility', orderable = False)
    class Meta:
        model = UserProjectBinding
        fields = ('id', 'project')
        sequence = ('id', 'project')
        attrs = { 
                 "class": "table table-striped table-bordered", 
                 "thead": { "class": "thead-dark table-sm" }, 
                 "td": { "style": "padding:.5ex" }, 
                 "th": { "style": "padding:.5ex", "class": "table-secondary" } 
                }


class TableJoinProject(tables.Table):
    class SelectColumn(tables.Column):
        def render(self, record):
            p = record.project
            template = f"""
<div class="form-check form-switch">
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
            images = set([ psb.service.image for psb in ProjectContainerBinding.objects.filter(project = p, container__user = p.creator) ])
            template = [ f"""
<div class="form-check form-switch">
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
    id = tables.Column(verbose_name = 'Collaboration', orderable = False)
    role = tables.Column(verbose_name = 'Admin role', empty_values = (), orderable = False)
    name = tables.Column(order_by = ('user__first_name', 'user__last_name'))

    class Meta:
        model = Profile
        fields = ('id', 'role', 'name')
        sequence = ('id', 'role', 'name')
        attrs = {
                 "class": "table table-striped table-bordered",
                 "thead": { "class": "thead-dark table-sm" },
                 "td": { "style": "padding:.5ex" },
                 "th": { "style": "padding:.5ex", "class": "table-secondary" }
                }

    def __init__(self, project, collaborators):
        self.project = project
        super(TableCollaborator, self).__init__(collaborators)

    def render_id(self, record):
        user = record.user
        if user in self.project.collaborators:
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

    def render_role(self, record):
        user = record.user
        if user in self.project.admins:
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

    def render_name(self, record):
        user = record.user
        return format_html(f'<span data-toggle="tooltip" title="Username {user.username}." data-placement="top" style="font-weight: bold;">{user.first_name}</span> {user.last_name}')


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
<div class="form-check form-switch">
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

 
