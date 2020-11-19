from django import forms
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
import django_tables2 as tables

from hub.models import UserProjectBinding
from hub.models import ProjectServiceBinding
from hub.models import Service

def image_column(service):
    class ImageColumn(tables.Column):
        def render(self, record):
            image = record.project.image
            return format_html(str(image)) if image == service.image else format_html("<strong>%s</strong>" % image)
    return ImageColumn

class CollaboratorColumn(tables.Column):
    def render(self, record):
        return format_html(', '.join(record.collaborators))


def table_projects(service):
    bound_projects = [ b.project for b in ProjectServiceBinding.objects.filter(service = service) ]

    class SelectColumn(tables.Column):
        def render(self, record):
            p = record.project
            if p in bound_projects:
                return format_html('<input type="hidden" name="project_ids_before" value="{0}"><input type="checkbox" name="project_ids_after" value="{0}" checked data-toggle="toggle" data-on="Attached" data-off="Detach" data-onstyle="success" data-offstyle="dark" data-size="xs">'.format(p.id))
            else:
                return format_html('<input type="checkbox" name="project_ids_after" data-toggle="toggle" value="{}" data-on="Attach" data-off="Unused" data-onstyle="success" data-offstyle="dark" data-size="xs">'.format(p.id))
    rc = SelectColumn

    class CollaboratorColumn(tables.Column):
        def render(self, record):
            p = record.project
            return format_html(', '.join(p.collaborators))
    cc = CollaboratorColumn

    class T_PROJECTS(tables.Table):
        id = rc(verbose_name = 'Select', orderable = False)
        project = tables.Column(orderable = False)
        collaborator = cc(verbose_name = 'Collaborators', orderable = False)
    
        class Meta:
            model = UserProjectBinding
            fields = ('id', 'project', 'collaborator')
            attrs = { "class": "table table-striped table-bordered", "thead": { "class": "thead-dark table-sm" }, "td": { "style": "padding:.5ex" } }

    return T_PROJECTS



class T_JOINABLEPROJECT(tables.Table):
    class SelectColumn(tables.Column):
        def render(self, record):
            p = record.project
            return format_html('<input type="checkbox" name="project_ids" data-toggle="toggle" value="{}" data-on="Join" data-off="Skip" data-onstyle="success" data-offstyle="dark" data-size="xs">'.format(p.id))
    id = SelectColumn(verbose_name = 'Select', orderable = False)
    class UserColumn(tables.Column):
        def render(self, record):
            user = record.user
            return format_html(f'<span data-toggle="tooltip" title="Username {user.username}." data-placement="top" style="font-weight: bold;">{user.first_name}</span> {user.last_name}')
    user = UserColumn(verbose_name = 'Creator name', order_by = ('user__first_name', 'user__last_name'))
    class ImageColumn(tables.Column):
        def render(self, record):
            p = record.project
            images = set([ psb.service.image for psb in ProjectServiceBinding.objects.filter(project = p, service__user = p.creator) ])
            image_selection = '<br>'.join([ f'<input type="checkbox" name="image_ids_{p.id}" data-toggle="toggle" value="{i.id}" data-on="Create service" data-off="Skip" data-onstyle="success" data-offstyle="dark" data-size="xs">{i.name}' for i in images ])
            return format_html(image_selection)
    images = ImageColumn(verbose_name = 'Service environment images', orderable = False, empty_values = ())

    class Meta:
        model = UserProjectBinding
        fields = ('id', 'project', 'user', 'images')
        sequence = ('id', 'project', 'user', 'images')
        attrs = { "class": "table table-striped table-bordered", "thead": { "class": "thead-dark table-sm" }, "td": { "style": "padding:.5ex" } }


class T_PROJECT(tables.Table):
    class ProjectSelectionColumn(tables.Column):
        def render(self, record):
            if record.is_hidden:
                return format_html('<input type="checkbox" name="selection" data-toggle="toggle" value="{0}" data-off="Show" data-on="Hidden" data-onstyle="dark" data-offstyle="success" data-size="xs" checked>'.format(record.id))
            else:
                return format_html('<input type="checkbox" name="selection" data-toggle="toggle" value="{0}" data-off="Shown" data-on="Hide" data-onstyle="dark" data-offstyle="success" data-size="xs">'.format(record.id))
    id = ProjectSelectionColumn(verbose_name = 'Visibility', orderable = False)
    class Meta:
        model = UserProjectBinding
        fields = ('id', 'project')
        sequence = ('id', 'project')
        attrs = { "class": "table table-striped table-bordered", "thead": { "class": "thead-dark table-sm" }, "td": { "style": "padding:.5ex" } }

def table_services(userprojectbinding):
    class T_PROJECTSERVICE(tables.Table):
        class ServiceSelectionColumn(tables.Column):
            def render(self, record):
                stl_add = 'danger' if record.state in [ record.ST_RUNNING, record.ST_NEED_RESTART ] else 'success'
                stl_rem = 'danger' if record.state in [ record.ST_RUNNING, record.ST_NEED_RESTART ] else 'dark'
                try:
                    psb = ProjectServiceBinding.objects.get(project = userprojectbinding.project, service = record)
                    return format_html(f'<input type="hidden" name="psb_ids_before" value="{psb.id}"><input type="checkbox" name="psb_ids_after" data-toggle="toggle" value="{psb.id}" data-on="Bound" data-off="Detach" data-onstyle="success" data-offstyle="{stl_rem}" data-size="xs" checked>')
                except ProjectServiceBinding.DoesNotExist:
                    return format_html(f'<input type="checkbox" name="svc_ids" data-toggle="toggle" value="{record.id}" data-off="Skip" data-on="Attach" data-onstyle="{stl_add}" data-offstyle="dark" data-size="xs">')

        id = ServiceSelectionColumn(verbose_name = 'Environment', orderable = False)
        class Meta:
            model = Service
            fields = ('id', 'name', 'image', 'state')
            sequence = ('id', 'name', 'image', 'state')
            attrs = { "class": "table table-striped table-bordered", "thead": { "class": "thead-dark table-sm" }, "td": { "style": "padding:.5ex" } }
    return T_PROJECTSERVICE
