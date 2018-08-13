from django import forms
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
import django_tables2 as tables

from hub.models import UserAssignmentBinding, Assignment

class SelectionColumn(tables.Column):
    def render(self, value):
      return format_html('<input type="checkbox" name="selection" value="%s">' % value)

class T_COLLECT_ASSIGNMENT(tables.Table):
    id = SelectionColumn(verbose_name = 'Select', orderable = False)
    
    class Meta:
        model = Assignment
        fields = ('id', 'name', 'folder', 'created_at', 'valid_from', 'expires_at', 'can_studentsubmit')
        sequence = ('id', 'name', 'folder', 'created_at', 'valid_from', 'expires_at', 'can_studentsubmit')
        attrs = { "class": "table-striped table-bordered", "td": { "style": "padding:.5ex" } }

class T_COLLECT_UABINDING(tables.Table):
    pass


class tableUserAssignmentCommon:
    def render_assignment(self, value):
        return format_html(
            "<span data-toggle='tooltip' title='Assigned by %s %s\nFolder: %s' data-placement='right'>%s</span>" % 
            (value.creator.first_name, value.creator.last_name, value.folder, value.name)
        )
    def render_user(self, value):
        return format_html(
            "<span data-toggle='tooltip' title='Username %s' data-placement='right'>%s %s</span>" % 
            (value.username, value.first_name, value.last_name)
        )

class T_CORRECT(tables.Table, tableUserAssignmentCommon):
    id = SelectionColumn(verbose_name = 'Select', orderable = False)
    class Meta:
        model = UserAssignmentBinding
        exclude = ('received_at', 'expires_at', 'corrector', 'corrected_at')
        attrs = { "class": "table-striped table-bordered", "td": { "style": "padding:.5ex" } }

class T_BIND(tables.Table, tableUserAssignmentCommon):
    selection = tables.Column(verbose_name = 'Select', empty_values = ())
    def render_valid_from(self, record):
        representation = "%d_%d" % (record.user.id, record.assignment.id)
        value_attr = "" if record.valid_from is None else str(record.valid_from)
        return format_html('<input type="text" name="valid_from_%s" data-placement="bottom" data-toggle="tooltip" id="id_valid_from_%s" class="datetimepicker" title="If unspecified the assignment folder is populated to students right away." %s/>' % (representation, representation, value_attr) )
    def render_expires_at(self, record):
        representation = "%d_%d" % (record.user.id, record.assignment.id)
        value_attr = "" if record.expires_at is None else str(record.expires_at)
        return format_html('<input type="text" name="expires_at_%s" data-placement="bottom" data-toggle="tooltip" id="id_expires_at_%s" class="datetimepicker" title="If unspecified either you or students need to take care of collecting or submitting assignments respectively." %s/>' % (representation, representation, value_attr) )
    def render_selection(self, record):
        representation = "%d_%d" % (record.user.id, record.assignment.id)
        return format_html('<input type="checkbox" name="binding_representation" id="cb_%s" value="%s" />' % (representation, representation) )
    
    class Meta:
        model = UserAssignmentBinding
        sequence = ('selection', 'user', 'assignment', 'valid_from', 'expires_at')
        exclude = ('id', 'state', 'received_at', 'submitted_at', 'corrector', 'corrected_at')
        attrs = { "class": "table-striped table-bordered", "td": { "style": "padding:.5ex" } }

class T_SUBMIT(tables.Table, tableUserAssignmentCommon):
    id = SelectionColumn(verbose_name = 'Select', orderable = False)
    folder = tables.Column(verbose_name = 'Folder', orderable = False, empty_values = ())
    course = tables.Column(verbose_name = 'Course', orderable = False, empty_values = ())
    def render_folder(self, record):
        return str(record.assignment.folder)
    def render_course(self, record):
        c = record.assignment.course
        return format_html('<span data-placement="bottom" data-toggle="tooltip" title="%s">%s</span>' % (c.description, c.courseid))
    class Meta:
        model = UserAssignmentBinding
        sequence = ('id', 'course', 'assignment', 'folder', 'received_at', 'expires_at', 'state')
        exclude = ('user', 'valid_from', 'submitted_at', 'corrector', 'corrected_at')
        attrs = { "class": "table-striped table-bordered", "td": { "style": "padding:.5ex" } }
