import json

#from django.utils.translation import gettext_lazy as _
from django.utils.safestring import mark_safe
from django.utils.html import format_html
from django.db import models
import django_tables2 as tables

from django.contrib.auth.models import User
from ..models import UserCourseBinding, UserAssignmentBinding, Assignment, UserCourseCodeBinding, Group, UserCourseGroupBinding

try:
    from kooplexhub.settings import KOOPLEX
except ImportError:
    KOOPLEX = {}

class TableAssignment(tables.Table):
    class AssignmentSelectionColumn(tables.Column):
        def render(self, record):
            if record.state in [ record.ST_WORKINPROGRESS, record.ST_SUBMITTED ]:
                return format_html(f"""
<div class="form-check form-switch">
  <input class="form-check-input" type="checkbox" id="uab-{record.id}" name="selection" value="{record.id}" />
</div>
                """)
            elif record.state in [ record.ST_COLLECTED, record.ST_CORRECTED, record.ST_QUEUED ]:
                return format_html(f"""
<span class="bi bi-hourglass-bottom" data-toggle="tooltip" title="{record.ST_LOOKUP[record.state]}" />
                """)
            else:
                return format_html(f"""
<span class="bi bi-hand-thumbs-up" data-toggle="tooltip" title="{record.ST_LOOKUP[record.state]}" />
                """)

    def render_course(self, record):
        return record.assignment.course.name

    def render_assignment(self, record):
        return record.assignment.name

    def render_expires_at(self, record):
        exp = record.expires_at if record.expires_at else "&mdash;"
        return format_html(f"""
<span class="bi bi-arrow-up-right-square-fill" data-toggle="tooltip" title="Submit count">{record.submit_count}</span>
<span class="bi bi-check-square-fill" data-toggle="tooltip" title="Correction count">{record.correction_count}</span>&nbsp; {exp}
        """)

    id = AssignmentSelectionColumn(verbose_name = 'Submit', orderable = False)
    course = tables.Column(orderable = False, empty_values = ())
    assignment = tables.Column(orderable = False)
    score = tables.Column(orderable = False)
    feedback_text = tables.Column(orderable = False)

    class Meta:
        model = UserAssignmentBinding
        fields = ('id', 'course', 'assignment', 'expires_at', 'score', 'feedback_text')
        attrs = { 
                 "class": "table table-striped table-bordered", 
                 "thead": { "class": "thead-dark table-sm" }, 
                 "td": { "style": "padding:.5ex" }, 
                 "th": { "style": "padding:.5ex", "class": "table-secondary" } 
                }


class TableAssignmentConf(tables.Table):
    class AssignmentSelectionColumn(tables.Column):
        def render(self, record):
            return format_html(f"""
<div class="form-check form-switch">
  <input class="form-check-input" type="checkbox" id="a-{record.id}" name="selection_delete" value="{record.id}" />
</div>
<input type="hidden" name="assignment_ids" value="{record.id}" />
            """)

    def render_course(self, record):
        return record.course.name

    def render_received(self, record):
        return len(UserAssignmentBinding.objects.filter(assignment = record))

    def render_valid_from(self, record):
        d = record.valid_from.strftime("%Y-%m-%d %H:%M") if record.valid_from else ''
        return format_html(f"""
<div class="input-append date" id="datetimepicker-valid-{record.id}" date-date="{d}" data-date-format="yyyy-mm-dd hh:ii">
    <input class="datetimepicker span2" size="16" type="text" value="{d}">
</div>
        """)

    def render_expires_at(self, record):
        d = record.expires_at.strftime("%Y-%m-%d %H:%M") if record.expires_at else ''
        return format_html(f"""
<div class="input-append date" id="datetimepicker-expiry-{record.id}" date-date="{d}" data-date-format="yyyy-mm-dd hh:ii">
    <input class="datetimepicker span2" size="16" type="text" value="{d}">
</div>
        """)

    def render_description(self, record):
        return format_html(f"""
<textarea class="form-textarea" id="description-{record.id}" name="description-{record.id}">{record.description}</textarea>
<input type="hidden" id="description-old-{record.id}" name="description-old-{record.id}" value="{record.description}" />
        """)

    def render_name(self, record):
        return format_html(f"""
<input class="form-text-input" type="text" id="name-{record.id}" name="name-{record.id}" value="{record.name}" />
<input type="hidden" id="name-old-{record.id}" name="name-old-{record.id}" value="{record.name}" />
        """)

    id = AssignmentSelectionColumn(verbose_name = 'Delete', orderable = False)
    course = tables.Column(orderable = False, empty_values = ())
    received = tables.Column(orderable = False, empty_values = ())
    class Meta:
        model = Assignment
        fields = ('id', 'course', 'creator', 'folder', 'name', 'description', 'created_at', 'valid_from', 'expires_at', 'received')
        attrs = { 
                 "class": "table table-striped table-bordered", 
                 "thead": { "class": "thead-dark table-sm" }, 
                 "td": { "style": "padding:.5ex" }, 
                 "th": { "style": "padding:.5ex", "class": "table-secondary" } 
                }

class TableAssignmentSummary(tables.Table):

    def render_course(self, record):
        return record.course.name

    def render_received(self, record):
        return len(UserAssignmentBinding.objects.filter(assignment = record))

#    id = AssignmentSelectionColumn(verbose_name = 'Delete', orderable = False)
    course = tables.Column(orderable = False, empty_values = ())
    received = tables.Column(orderable = False, empty_values = ())
    class Meta:
        model = Assignment
        fields = ('course', 'creator', 'folder', 'name', 'description', 'created_at', 'valid_from', 'expires_at', 'received')
        attrs = { 
                 "class": "table table-striped table-bordered", 
                 "thead": { "class": "thead-dark table-sm" }, 
                 "td": { "style": "padding:.5ex" }, 
                 "th": { "style": "padding:.5ex", "class": "table-secondary" } 
                }


class TableAssignmentCollect(tables.Table):
    def render_id(self, record):
        if record.id is None:
            return format_html(f"""
<div class="form-check form-switch">
  <input class="form-check-input" type="checkbox" id="uab-{record.assignment.id}-{record.user.id}" name="selection_handout" value="[{record.assignment.id}, {record.user.id}]" />
  <label class="form-check-label" for="uab-{record.assignment.id}-{record.user.id}" id="lbl_uab-{record.assignment.id}-{record.user.id}"> <span class="bi bi-box-arrow-up-right" data-toggle="tooltip" title="Hand out"></span></label>
</div>
            """)
        elif record.state == record.ST_WORKINPROGRESS:
            return format_html(f"""
<div class="form-check form-switch">
  <input class="form-check-input" type="checkbox" id="uab-{record.id}" name="selection_collect" value="{record.id}" />
  <label class="form-check-label" for="uab-{record.id}" id="lbl_uab-{record.id}"> <span class="bi bi-box-arrow-in-down-right" data-toggle="tooltip" title="Collect"></span></label>
</div>
            """)
        elif record.state in [ record.ST_COLLECTED, record.ST_SUBMITTED]:
            return format_html(f"""
<div class="form-check form-switch">
  <input class="form-check-input" type="checkbox" id="uab-{record.id}" name="selection_correct" value="{record.id}" />
  <label class="form-check-label" for="uab-{record.id}" id="lbl_uab-{record.id}"> <span class="bi bi-check-square-fill" data-toggle="tooltip" title="Correct"></span></label>
</div>
            """)
        elif record.state == record.ST_CORRECTED:
            return format_html(f"""
<div class="form-check form-switch">
  <input class="form-check-input" type="checkbox" id="uab-{record.id}" name="selection_finalize" value="{record.id}" />
  <label class="form-check-label" for="uab-{record.id}" id="lbl_uab-{record.id}"> <span class="bi bi-check-square" data-toggle="tooltip" title="Finalize"></span></label>
</div>
            """)
        elif record.state == record.ST_READY:
            return format_html(f"""
<div class="form-check form-switch">
  <input class="form-check-input" type="checkbox" id="uab-{record.id}" name="selection_reassign" value="{record.id}" />
  <label class="form-check-label" for="uab-{record.id}" id="lbl_uab-{record.id}"> <span class="bi bi-recycle" data-toggle="tooltip" title="Reassign"</span></label>
</div>
            """)

    def render_course(self, record):
        try:
            g = UserCourseGroupBinding.objects.get(usercoursebinding__user = record.user, usercoursebinding__course = record.assignment.course).group
            return f"{record.assignment.course.name} ({g.name})"
        except UserCourseGroupBinding.DoesNotExists:
            return record.assignment.course.name

    def render_assignment(self, record):
        return record.assignment.name
    
    def render_user(self, record):
        user = record.user
        return format_html(f"{user.first_name} {user.last_name} / {user.username}")

    def render_score(self, record):
        s = record.score if record.score else ''
        if record.state == record.ST_CORRECTED:
            return format_html(f"""
<input class="form-text-input" type="text" id="score-{record.id}" name="score-{record.id}" value="{s}" onchange="set_checkbox('uab-{record.id}');" />
            """)
        elif record.state == record.ST_READY:
            return format_html(f"""
<input class="form-text-input" type="text" id="score-{record.id}" name="score-{record.id}" value="{s}" />
<input type="hidden" name="score-old-{record.id}" value="{s}" />
<input type="hidden" name="ready_ids" value="{record.id}" />
            """)
        else:
            return record.score if record.score else format_html('—')

    def render_feedback_text(self, record):
        t = record.feedback_text if record.feedback_text else ''
        if record.state == record.ST_CORRECTED:
            return format_html(f"""
<textarea class="form-textarea" id="feedback_text-{record.id}" name="feedback_text-{record.id}" onchange="set_checkbox('uab-{record.id}');">{t}</textarea>
<input type="hidden" name="feedback_text-old-{record.id}" value="{t}" />
            """)
        elif record.state == record.ST_READY:
            return format_html(f"""
<textarea class="form-textarea" id="feedback_text-{record.id}" name="feedback_text-{record.id}">{t}</textarea>
<input type="hidden" name="feedback_text-old-{record.id}" value="{t}" />
            """)
        else:
            return t

    id = tables.Column(verbose_name = 'Operation', orderable = False, empty_values = ())
    course = tables.Column(orderable = False, empty_values = ())
    score = tables.Column(orderable = False, empty_values = ())
    feedback_text = tables.Column(orderable = False, empty_values = ())
    submit_count = tables.Column(orderable = False)
    correction_count = tables.Column(orderable = False)
    
    class Meta:
        model = UserAssignmentBinding
        fields = ('id', 'course', 'assignment', 'user', 'expires_at', 'submit_count', 'correction_count', 'score', 'feedback_text')
        attrs = { 
                 "class": "table table-striped table-bordered", 
                 "thead": { "class": "thead-dark table-sm" }, 
                 "td": { "style": "padding:.5ex" }, 
                 "th": { "style": "padding:.5ex", "class": "table-secondary" } 
                }


class TableAssignmentMass(tables.Table):
    @staticmethod
    def uab(record, state = None, group = None):
        if state and not isinstance(state, list):
            state = [ state ]
        if group:
            users = TableAssignmentMass._students(record, group)
            return UserAssignmentBinding.objects.filter(assignment = record, state__in = state, user__in = users) \
                    if state else UserAssignmentBinding.objects.filter(assignment = record, user__in = users)
        else:
            return UserAssignmentBinding.objects.filter(assignment = record, state__in = state) if state else UserAssignmentBinding.objects.filter(assignment = record)

    @staticmethod
    def _students(record, group = None):
        if group:
            return [ ucgb.usercoursebinding.user for ucgb in UserCourseGroupBinding.objects.filter(usercoursebinding__course = record.course, group = group) ]
        else:
            return [ ucb.user for ucb in UserCourseBinding.objects.filter(course = record.course, is_teacher = False) ]

    @staticmethod
    def usr(record, group = None):
        users = TableAssignmentMass._students(record, group)
        bound = [ b.user for b in TableAssignmentMass.uab(record, group = group) ]
        return set(users).difference(bound)

    class AssignmentSelectionColumn(tables.Column):
        def render(self, record):
            def switch(prefix, title, icon, record, uabs, group):
                n = len(uabs)
                if n == 0:
                    return
                g = group.id if group else 0
                gn = group.name if group else ''
                ids = json.dumps([ (record.id, u.id) for u in uabs ]) if prefix == 'assign' else json.dumps([ uab.id for uab in uabs ]) 
                return (f"""
<div class="form-check form-switch">
  <input class="form-check-input" type="checkbox" id="{prefix}-{record.id}-{g}" name="{prefix}_selection" value="{ids}" />
  <label class="form-check-label" for="{prefix}-{record.id}-{g}" id="lbl_{prefix}-{record.id}-{g}"> <span class="bi {icon}" data-toggle="tooltip" title="{title}"> {gn} ({n})</span></label>
</div>
                """)
            buttons = []
            for g in record.course.groups:
                buttons.append(switch('collect', 'Collect', 'bi-box-arrow-in-down-right', record, TableAssignmentMass.uab(record, state = UserAssignmentBinding.ST_WORKINPROGRESS, group = g), g))
                buttons.append(switch('correct', 'Correct', 'bi-check-square-fill', record, TableAssignmentMass.uab(record, state = [ UserAssignmentBinding.ST_SUBMITTED, UserAssignmentBinding.ST_COLLECTED ], group = g), g))
                buttons.append(switch('assign', 'Hand out', 'bi-box-arrow-up-right', record, TableAssignmentMass.usr(record, group = g), g))
            if len(record.course.groups) == 0:
                buttons.append(switch('collect', 'Collect', 'bi-box-arrow-in-down-right', record, TableAssignmentMass.uab(record, state = UserAssignmentBinding.ST_WORKINPROGRESS), None))
                buttons.append(switch('correct', 'Correct', 'bi-check-square-fill', record, TableAssignmentMass.uab(record, state = [ UserAssignmentBinding.ST_SUBMITTED, UserAssignmentBinding.ST_COLLECTED ]), None))
                buttons.append(switch('assign', 'Hand out', 'bi-box-arrow-up-right', record, TableAssignmentMass.usr(record), None))
            buttons = list(filter(lambda x: x, buttons))
            return format_html('<br>'.join(buttons)) if len(buttons) else "-"

    id = AssignmentSelectionColumn(verbose_name = 'Operation', orderable = False)
    def render_course(self, record):
        return record.course.name
    def render_work_in_progress(self, record):
        return len(self.uab(record, UserAssignmentBinding.ST_WORKINPROGRESS))
    def render_submitted(self, record):
        return len(self.uab(record, UserAssignmentBinding.ST_SUBMITTED))
    def render_collected(self, record):
        return len(self.uab(record, UserAssignmentBinding.ST_COLLECTED))
    def render_correcting(self, record):
        return len(self.uab(record, UserAssignmentBinding.ST_CORRECTED))
    def render_ready(self, record):
        return len(self.uab(record, UserAssignmentBinding.ST_READY))
    def render_students(self, record):
        return len(self._students(record))
    #FIXME: def render_expire_at(self): n_out < n_studs --> datetime picker
    students = tables.Column(orderable = False, empty_values = ())
    work_in_progress = tables.Column(orderable = False, empty_values = ())
    submitted = tables.Column(orderable = False, empty_values = ())
    collected = tables.Column(orderable = False, empty_values = ())
    correcting = tables.Column(orderable = False, empty_values = ())
    ready = tables.Column(orderable = False, empty_values = ())
    class Meta:
        model = Assignment
        fields = ('id', 'course', 'name', 'expires_at', 'students', 'work_in_progress', 'submitted', 'collected', 'correcting', 'ready')
        attrs = { 
                 "class": "table table-striped table-bordered", 
                 "thead": { "class": "thead-dark table-sm" }, 
                 "td": { "style": "padding:.5ex" }, 
                 "th": { "style": "padding:.5ex", "class": "table-secondary" } 
                }


class TableUser(tables.Table):
    def render_id(self, record):
        f = 'teacher' if self.teacher_selector else 'student'
        try:
            ucb = UserCourseBinding.objects.get(course = self.course, user = record, is_teacher = self.teacher_selector)
            return format_html(f"""
<div class="form-check form-switch">
  <input class="form-check-input" type="checkbox" id="ur-{ucb.id}" name="selection_{f}_removal" value="{ucb.id}" />
  <label class="form-check-label" for="ur-{ucb.id}" id="lbl_ur-{ucb.id}"> Remove</label>
</div>
            """)
        except:# UserCourseBinding.NotExists:
            return format_html(f"""
<div class="form-check form-switch">
  <input class="form-check-input" type="checkbox" id="u-{record.id}" name="selection_{f}" value="{record.id}" />
  <label class="form-check-label" for="u-{record.id}" id="lbl_u-{record.id}"> Add</label>
</div>
            """)

    def render_name(self, record):
        return format_html(f"""
<span data-toggle="tooltip" title="username: {record.username}\nemail: {record.email}"><i class="bi bi-info-square-fill" ></i>&nbsp;{record.first_name} <b>{record.last_name}</b></span>
        """)

    def render_course(self, record):
        return format_html(", ".join([ ucb.course.name for ucb in UserCourseBinding.objects.filter(user = record) ]))

    def render_coursecode(self, record):
        return ", ".join([ ucb.coursecode.courseid for ucb in UserCourseCodeBinding.objects.filter(user = record) ])

    id = tables.Column(verbose_name = 'Operation', orderable = False)
    course = tables.Column(orderable = False, empty_values = ())
    name = tables.Column(orderable = False, empty_values = ())
    coursecode = tables.Column(orderable = False, empty_values = ())

    class Meta:
        model = User
        fields = ('id', 'course', 'name', 'coursecode')
        attrs = { 
                 "class": "table table-striped table-bordered", 
                 "thead": { "class": "thead-dark table-sm" }, 
                 "td": { "style": "padding:.5ex" }, 
                 "th": { "style": "padding:.5ex", "class": "table-secondary" } 
                }

    def __init__(self, course, teacher_selector, pattern, *args, **kwargs):
        complementary_users = [ ucb.user.username for ucb in UserCourseBinding.objects.filter(course = course, is_teacher = not teacher_selector) ]
        if pattern:
            users = User.objects.filter(models.Q(username__icontains = pattern) | models.Q(first_name__icontains = pattern) | models.Q(last_name__icontains = pattern) | models.Q(usercoursecodebinding__coursecode__courseid__icontains = pattern)).exclude(username__in = KOOPLEX.get('blacklist', ['hubadmin', 'admin'])).exclude(username__in = complementary_users).distinct()
        else:
            users = User.objects.all().exclude(username__in = KOOPLEX.get('blacklist', ['hubadmin', 'admin'])).exclude(username__in = complementary_users)
        super(TableUser, self).__init__(users)
        self.course = course
        self.teacher_selector = teacher_selector
        self.not_empty = len(users) > 0


class TableGroup(tables.Table):
    def render_id(self, record):
        return format_html(f"""
<div class="form-check form-switch">
  <input class="form-check-input" type="checkbox" id="g-{record.id}" name="selection_group_removal" value="{record.id}" />
  <label class="form-check-label" for="g-{record.id}" id="lbl_g-{record.id}"> Remove</label>
</div>
        """)

    def render_name(self, record):
        return format_html(f"""
<input type="hidden" name="name-before-{record.id}" value="{record.name}">
<input type="text" name="name-{record.id}" value="{record.name}">
        """)

    def render_description(self, record):
        return format_html(f"""
<input type="hidden" name="description-before-{record.id}" value="{record.description}">
<textarea name="description-{record.id}">{record.description}</textarea>
        """)

    id = tables.Column(verbose_name = 'Operation', orderable = False)
    course = tables.Column(orderable = False, empty_values = ())
    name = tables.Column(orderable = False, empty_values = ())
    description = tables.Column(orderable = False, empty_values = ())

    class Meta:
        model = Group
        fields = ('id', 'course', 'name', 'description')
        attrs = { 
                 "class": "table table-striped table-bordered", 
                 "thead": { "class": "thead-dark table-sm" }, 
                 "td": { "style": "padding:.5ex" }, 
                 "th": { "style": "padding:.5ex", "class": "table-secondary" } 
                }


