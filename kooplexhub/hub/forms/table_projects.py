from django import forms
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
import django_tables2 as tables

from hub.models import UserProjectBinding
from hub.models import ProjectServiceBinding

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
            attrs = { "class": "table-striped table-bordered", "td": { "style": "padding:.5ex" } }

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
        attrs = { "class": "table-striped table-bordered", "td": { "style": "padding:.5ex" } }
