#from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
import django_tables2 as tables

from ..models import UserVolumeBinding
#from ..models import VolumeContainerBinding
#from container.models import Container
from hub.models import Profile

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

    def __init__(self, volume, collaborators):
        self.volume = volume
        super(TableCollaborator, self).__init__(collaborators)

    def render_id(self, record):
        user = record.user
        if user in self.volume.collaborators:
            template = f"""
  <div class="container" style="width: 170px">
    <div class="row" style="width: 170px">
  <div class="col-sm"><span>Add</span></div>
<div class="form-check col-sm form-switch">
  <input type="hidden" name="collaborator_ids_before" value="{user.id}" />
  <input class="form-check-input" type="checkbox" id="cb_id-{user.id}" name="collaborator_ids_after" value="{user.id}" checked />
  <label class="form-check-label" for="cb_id-{user.id}"> Remove</label>
</div>
</div>
</div>
            """
        else:
            template = f"""
              <div class="container" style="width: 170px">
                  <div class="row" style="width: 170px">
                    <div class="col-sm"><span>Add</span></div>
<div class="form-check col-sm form-switch">
  <input class="form-check-input" type="checkbox" id="cb_id-{user.id}" name="collaborator_ids_after" value="{user.id}" />
  <label class="form-check-label" for="cb_id-{user.id}">Remove</label>
</div>
</div>
</div>
            """
        return format_html(template)

    def render_role(self, record):
        user = record.user
        if user in self.volume.admins:
            template = f"""
 <div class="container" style="width: 170px">
                  <div class="row" style="width: 170px">
                    <div class="col-sm"><span>Grant</span></div>
<div class="form-check col-sm form-switch">
  <input class="form-check-input" type="checkbox" id="cb_admid-{user.id}" name="admin_ids_after" value="{user.id}" checked />
  <label class="form-check-label" for="cb_admid-{user.id}"> Revoke</label>
</div>
</div>
</div>
            """
        else:
            template = f"""
                          <div class="container" style="width: 170px">
                  <div class="row" style="width: 170px">
                    <div class="col-sm"><span>Grant</span></div>
<div class="form-check col-sm form-switch">
  <input class="form-check-input" type="checkbox" id="cb_admid-{user.id}" name="admin_ids_after" value="{user.id}" />
  <label class="form-check-label" for="cb_admid-{user.id}"> Revoke</label>
</div>
</div>
</div>
            """
        return format_html(template)

    def render_name(self, record):
        user = record.user
        return format_html(f'<span data-toggle="tooltip" title="Username {user.username}." data-placement="top" style="font-weight: bold;">{user.first_name}</span> {user.last_name}')


#class TableVolumeContainer(tables.Table):
#    id = tables.Column(verbose_name = 'Template', orderable = False)
#
#    class Meta:
#        model = VolumeContainerBinding
#        fields = ('id', 'container__name', 'container__state')
#        attrs = {
#                     "class": "table table-striped table-bordered",
#                     "thead": { "class": "thead-dark table-sm" },
#                     "td": { "style": "padding:.5ex" },
#                     "th": { "style": "padding:.5ex", "class": "table-secondary" }
#                    }
#
#    def render_id(self, record):
#        template = f"""
#<div class="form-check">
#  <input class="form-check-input" type="checkbox" id="cb_svcid-{record.id}" name="service_ids" value="{record.id}" />
#  <label class="form-check-label" for="cb_svid-{record.id}"> Create</label>
#</div>
#        """
#        return format_html(template)
#
#
#class TableContainer(tables.Table):
#    id = tables.Column(verbose_name = 'Environment', orderable = False)
#
#    class Meta:
#        model = Container
#        fields = ('id', 'name', 'image', 'state')
#        sequence = ('id', 'name', 'image', 'state')
#        attrs = { 
#                 "class": "table table-striped table-bordered", 
#                 "thead": { "class": "thead-dark table-sm" }, 
#                 "td": { "style": "padding:.5ex" }, 
#                 "th": { "style": "padding:.5ex", "class": "table-secondary" } 
#                }
#
#    def __init__(self, uservolumebinding, containers):
#        super(TableContainer, self).__init__(containers)
#        self.uvb = uservolumebinding
#
#    def render_id(self, record):
#        stl_add = 'danger' if record.state in [ record.ST_RUNNING, record.ST_NEED_RESTART ] else 'success'
#        stl_rem = 'danger' if record.state in [ record.ST_RUNNING, record.ST_NEED_RESTART ] else 'dark'
#        try:
#            psb = VolumeContainerBinding.objects.get(volume = self.uvb.volume, container = record)
#            template = f"""
#<div class="form-check form-switch">
#  <input type="hidden" name="psb_ids_before" value="{psb.id}">
#  <input class="form-check-input" type="checkbox" id="cb_psbid-{psb.id}" name="psb_ids_after" value="{psb.id}" checked />
#  <label class="form-check-label" for="cb_psbid-{psb.id}"> Keep added</label>
#</div>
#            """
#        except VolumeContainerBinding.DoesNotExist:
#            template = f"""
#<div class="form-check form-switch">
#  <input class="form-check-input" type="checkbox" id="cb_svc-{record.id}" name="svc_ids" value="{record.id}" />
#  <label class="form-check-label" for="cb_svcid-{record.id}"> Attach</label>
#</div>
#            """
#        return format_html(template)
#
#
##FIXME:  from hub.models import Service
##FIXME:  
##FIXME:  def image_column(service):
##FIXME:      class ImageColumn(tables.Column):
##FIXME:          def render(self, record):
##FIXME:              image = record.volume.image
##FIXME:              return format_html(str(image)) if image == service.image else format_html("<strong>%s</strong>" % image)
##FIXME:      return ImageColumn
##FIXME:  
##FIXME:  class CollaboratorColumn(tables.Column):
##FIXME:      def render(self, record):
##FIXME:          return format_html(', '.join(record.collaborators))
##FIXME:  
##FIXME:  

 
