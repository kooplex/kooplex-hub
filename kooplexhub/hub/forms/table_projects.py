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

class SelectColumn(tables.Column):
    def render(self, record):
        p = record.project
        return format_html("<input type='checkbox' name='project_ids' value='%d'>" % (p.id))

class ProjectColumn(tables.Column):
    def render(self, record):
        p = record.project
        return format_html("%s (%s)" % (p.name, p.image))

class UserColumn(tables.Column):
    def render(self, record):
        u = record.user
        return format_html("%s %s (%s)" % (u.first_name, u.last_name, u.username))

class T_JOINABLEPROJECT(tables.Table):
    id = SelectColumn(verbose_name = 'Select', orderable = False)
    project = ProjectColumn(verbose_name = 'Project (image)', orderable = False)
    user = UserColumn(verbose_name = 'Creator name', orderable = False)
    class Meta:
        model = UserProjectBinding
        fields = ('id', 'project', 'user')
        sequence = ('id', 'project', 'user')
        attrs = { "class": "table-striped table-bordered", "td": { "style": "padding:.5ex" } }
