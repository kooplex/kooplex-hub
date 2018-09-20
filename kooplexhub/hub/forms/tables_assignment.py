from django import forms
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
import django_tables2 as tables

from hub.models import UserAssignmentBinding, Assignment

def selectioncolumn(name):
    widget_str = '<input type="checkbox" name="%s" value="%%s">' % name
    class SelectionColumn(tables.Column):
        def render(self, value):
          return format_html(widget_str % value)
    return SelectionColumn

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

col_assignmentIDs = selectioncolumn('assignment_ids')

class T_COLLECT_ASSIGNMENT(tables.Table):
    id = col_assignmentIDs(verbose_name = 'Select', orderable = False)

    class Meta:
        model = Assignment
        fields = ('id', 'name', 'folder', 'created_at', 'valid_from', 'expires_at', 'can_studentsubmit')
        sequence = ('id', 'name', 'folder', 'created_at', 'valid_from', 'expires_at', 'can_studentsubmit')
        attrs = { "class": "table-striped table-bordered", "td": { "style": "padding:.5ex" } }

col_userassignmentbindingIDs = selectioncolumn('userassignmentbinding_ids')

class T_COLLECT_UABINDING(tables.Table, tableUserAssignmentCommon):
    id = col_userassignmentbindingIDs(verbose_name = 'Select', orderable = False)
    class Meta:
        model = UserAssignmentBinding
        sequence = ('id', 'user', 'assignment', 'received_at', 'expires_at', 'state')
        exclude = ('valid_from', 'submitted_at', 'corrector', 'corrected_at')
        attrs = { "class": "table-striped table-bordered", "td": { "style": "padding:.5ex" } }

class RadioSelectIDColumn(tables.Column):
    def render(self, record):
        if record.state in [ UserAssignmentBinding.ST_SUBMITTED, UserAssignmentBinding.ST_COLLECTED ]:
            return format_html("""
<input type="radio" name="task_%s" value="skip" checked> skip<br>
<input type="radio" name="task_%s" value="correct"> correct<br>
            """ % (record.id, record.id))
        elif record.state == UserAssignmentBinding.ST_CORRECTING:
            return format_html("""
<input type="radio" name="task_%s" value="skip" checked> skip<br>
<input type="radio" name="task_%s" value="ready"> ready<br>
<input type="radio" name="task_%s" value="reassign"> reassign
            """ % (record.id, record.id, record.id))
        elif record.state == UserAssignmentBinding.ST_FEEDBACK:
            return format_html("""
<input type="radio" name="task_%s" value="skip" checked> skip<br>
<input type="radio" name="task_%s" value="reassign"> reassign
            """ % (record.id, record.id, record.id))
        elif record.state == UserAssignmentBinding.ST_WORKINPROGRESS and record.corrector is not None:
            return format_html("""
<input type="radio" name="task_%s" value="skip" checked> skip<br>
<input type="radio" name="task_%s" value="ready"> ready
            """ % (record.id, record.id, record.id))
        else:
            return "—"

class T_CORRECT(tables.Table, tableUserAssignmentCommon):
    id = RadioSelectIDColumn(verbose_name = 'Select', orderable = False) #col_userassignmentbindingIDs(verbose_name = 'Select', orderable = False)
    score = tables.Column(empty_values = (), orderable = False)
    feedback_text = tables.Column(empty_values = (), orderable = False)

    def render_score(self, record):
        representation = "score_%d" % (record.id)
        value_attr = "" if record.score is None else str(record.score)
        return format_html('<input type="text" name="%s" id="%s" value="%s" style="width: 3em"/>' % (representation, representation, value_attr) )

    def render_feedback_text(self, record):
        representation = "feedback_text_%d" % (record.id)
        value_attr = "" if record.feedback_text is None else str(record.feedback_text)
        return format_html('<textarea name="%s" id="%s" cols="30">%s</textarea>' % (representation, representation, value_attr) )

    class Meta:
        model = UserAssignmentBinding
        exclude = ('received_at', 'valid_from', 'expires_at', 'corrected_at')
        attrs = { "class": "table-striped table-bordered", "td": { "style": "padding:.5ex" } }

class T_BIND(tables.Table, tableUserAssignmentCommon):
    selection = tables.Column(verbose_name = 'Select', empty_values = (), orderable = False)
    valid_from = tables.DateTimeColumn(verbose_name = 'Handout', orderable = False, empty_values = ())
    expires_at = tables.DateTimeColumn(verbose_name = 'Collect', orderable = False, empty_values = ())
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

class StudentSelectionColumn(tables.Column):
    def render(self, record):
        active = record.state in [ UserAssignmentBinding.ST_WORKINPROGRESS, UserAssignmentBinding.ST_SUBMITTED ]
        return format_html('<input type="checkbox" name="userassignmentbinding_ids" value="%s">' % record.id) if active else '—'

class T_SUBMIT(tables.Table, tableUserAssignmentCommon):
    id = StudentSelectionColumn(verbose_name = 'Select', orderable = False)
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
