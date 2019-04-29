from django import forms
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
import django_tables2 as tables

from hub.models import UserAssignmentBinding, Assignment


class common:
    def render_user(self, value):
        return format_html('%s %s' % (value.first_name, value.last_name))

    def render_username(self, record):
        return format_html(record.user.username)

    def render_assignment(self, value):
        return format_html(
            "<span data-toggle='tooltip' title='Assigned by %s %s\nFolder: %s' data-placement='right'>%s</span>" % 
            (value.creator.first_name, value.creator.last_name, value.folder, value.name)
        )



class T_BIND_ASSIGNMENT(tables.Table, common):
    selection = tables.Column(verbose_name = 'Select', empty_values = (), orderable = False)
    username = tables.Column(verbose_name = 'Username', orderable = False, empty_values = ())
    valid_from = tables.DateTimeColumn(verbose_name = 'Handout', orderable = False, empty_values = ())
    expires_at = tables.DateTimeColumn(verbose_name = 'Collect', orderable = False, empty_values = ())

    def render_selection(self, record):
        representation = "%d_%d" % (record.user.id, record.assignment.id)
        return format_html('<input type="checkbox" name="binding_representation" id="cb_%s" value="%s" />' % (representation, representation) )
    
    def render_valid_from(self, record):
        representation = "%d_%d" % (record.user.id, record.assignment.id)
        value_attr = "" if record.valid_from is None else str(record.valid_from)
        return format_html('<input type="text" name="valid_from_%s" data-placement="bottom" data-toggle="tooltip" id="id_valid_from_%s" class="datetimepicker" title="If unspecified the assignment folder is populated to students right away." %s/>' % (representation, representation, value_attr) )

    def render_expires_at(self, record):
        representation = "%d_%d" % (record.user.id, record.assignment.id)
        value_attr = "" if record.expires_at is None else str(record.expires_at)
        return format_html('<input type="text" name="expires_at_%s" data-placement="bottom" data-toggle="tooltip" id="id_expires_at_%s" class="datetimepicker" title="If unspecified either you or students need to take care of collecting or submitting assignments respectively." %s/>' % (representation, representation, value_attr) )

    class Meta:
        model = UserAssignmentBinding
        sequence = ('selection', 'user', 'username', 'assignment', 'valid_from', 'expires_at')
        exclude = ('id', 'state', 'received_at', 'submitted_at', 'corrector', 'corrected_at', 'score', 'feedback_text')
        attrs = { "class": "table-striped table-bordered", "td": { "style": "padding:.5ex" } }



class T_COLLECT_ASSIGNMENT(tables.Table, common):
    id = tables.Column(verbose_name = 'Select', orderable = False)
    username = tables.Column(verbose_name = 'Username', orderable = False, empty_values = ())

    def render_id(self, value):
          return format_html('<input type="checkbox" name="userassignmentbinding_ids" value="%s">' % value)

    class Meta:
        model = UserAssignmentBinding
        sequence = ('id', 'user', 'username', 'assignment', 'received_at', 'expires_at', 'state')
        exclude = ('valid_from', 'submitted_at', 'corrector', 'corrected_at')
        attrs = { "class": "table-striped table-bordered", "td": { "style": "padding:.5ex" } }



class T_FEEDBACK_ASSIGNMENT(tables.Table, common):
    id = tables.Column(verbose_name = 'Select', orderable = False)
    username = tables.Column(verbose_name = 'Username', orderable = False, empty_values = ())
    score = tables.Column(verbose_name = 'Score', orderable = False, empty_values = ())
    feedback_text = tables.Column(verbose_name = 'Feedback', orderable = False, empty_values = ())

    def render_id(self, record):
        if record.state in [ UserAssignmentBinding.ST_SUBMITTED, UserAssignmentBinding.ST_COLLECTED ]:
            return format_html("""
<input type="radio" name="task_%s" value="skip" checked> skip<br>
<input type="radio" name="task_%s" value="correct"> correct<br>
            """ % (record.id, record.id))
        elif record.state in [ UserAssignmentBinding.ST_CORRECTING, UserAssignmentBinding.ST_FEEDBACK ]:
            return format_html("""
<input type="radio" name="task_%s" value="skip" checked> skip<br>
<input type="radio" name="task_%s" value="ready" id="task_%s"> ready<br>
<input type="radio" name="task_%s" value="reassign"> reassign
            """ % (record.id, record.id, record.id, record.id))
        elif record.state == UserAssignmentBinding.ST_WORKINPROGRESS and record.corrector is not None:
            return format_html("""
<input type="radio" name="task_%s" value="skip" checked> skip<br>
<input type="radio" name="task_%s" value="ready" id="task_%s"> ready
            """ % (record.id, record.id, record.id))
        else:
            return format_html("—")

    def render_score(self, record):
        representation = "score_%d" % (record.id)
        value_attr = "" if record.score is None else str(record.score)
        return format_html('<input type="text" name="%s" id="%s" what="task_%d" value="%s" style="width: 3em"/>' % (representation, representation, record.id, value_attr) )
  
    def render_feedback_text(self, record):
        representation = "feedback_text_%d" % (record.id)
        value_attr = "" if record.feedback_text is None else str(record.feedback_text)
        return format_html('<textarea name="%s" what="task_%d" id="%s" cols="30">%s</textarea>' % (representation, record.id, representation, value_attr) )

    class Meta:
        model = UserAssignmentBinding
        sequence = ('id', 'user', 'username', 'assignment', 'received_at', 'expires_at', 'state', 'score', 'feedback_text')
        exclude = ('valid_from', 'submitted_at', 'corrector', 'corrected_at')
        attrs = { "class": "table-striped table-bordered", "td": { "style": "padding:.5ex" } }



class T_SUBMIT_ASSIGNMENT(tables.Table):
    id = tables.Column(verbose_name = 'Submit', orderable = False, empty_values = ())
    corrector = tables.Column(verbose_name = 'Corrector', orderable = False, empty_values = ())

    def render_id(self, record):
        if record.state in [ UserAssignmentBinding.ST_WORKINPROGRESS, UserAssignmentBinding.ST_SUBMITTED ]:
            return format_html('<input type="checkbox" name="userassignmentbinding_ids" value="%d">' % record.id)
        else:
            return format_html("—")

    def render_corrector(self, value):
        return format_html('%s %s' % (value.first_name, value.last_name)) if value else format_html("—")

    def render_folder(self, record):
        return str(record.assignment.folder)

    def render_assignment(self, value):
        return format_html('<span data-placement="bottom" data-toggle="tooltip" title="folder: %s">%s</span>' % (value.safename, value.name))

    class Meta:
        model = UserAssignmentBinding
        sequence = ('id', 'assignment', 'expires_at', 'state', 'corrector', 'corrected_at', 'score', 'feedback_text')
        exclude = ('user', 'received_at', 'valid_from', 'submitted_at')
        attrs = { "class": "table-striped table-bordered", "td": { "style": "padding:.5ex" } }
