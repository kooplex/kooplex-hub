import json

from django.utils.translation import gettext_lazy as _
from django.utils.safestring import mark_safe
from django.utils.html import format_html
from django.db import models
import django_tables2 as tables
from django.contrib.auth.models import User

from education.models import UserCourseBinding, UserAssignmentBinding, Assignment, UserCourseCodeBinding, CourseGroup, UserCourseGroupBinding
from hub.templatetags.extras import render_user as ru
from hub.templatetags.extras import render_date as rd
from hub.templatetags.extras import render_folder as rf

from kooplexhub.common import table_attributes

try:
    from kooplexhub.settings import KOOPLEX
except ImportError:
    KOOPLEX = {}

ta_light = table_attributes.copy()
ta_light.update({ "td": { "class": "p-1 text-light" } })

class TableAssignment(tables.Table):
    class Meta:
        model = UserAssignmentBinding
        fields = ('course', 'assignment', 'score', 'feedback_text')
        sequence = ('button', 'course', 'assignment', 'info', 'score', 'feedback_text')
        attrs = ta_light

    button = tables.Column(verbose_name = 'Select/Jump', orderable = False, empty_values = ())
    course = tables.Column(orderable = False, empty_values = ())
    assignment = tables.Column(orderable = False)
    info = tables.Column(orderable = False, empty_values = ())
    score = tables.Column(orderable = False, empty_values = ())
    feedback_text = tables.Column(orderable = False, empty_values = ())


    def _render_button(self, record):
        if record.state == record.ST_WORKINPROGRESS:
            return format_html(f"""
<div class="form-check form-switch">
  <input class="form-check-input" type="checkbox" name="userassignmentbinding_ids" name="selection" value="{record.id}" />
</div>
            """)
        elif record.state in [ record.ST_SUBMITTED, record.ST_COLLECTED ]:
            return format_html(f"""
<span class="bi bi-hand-thumbs-up" data-toggle="tooltip" title="{record.ST_LOOKUP[record.state]}" />
            """)
        elif record.state == record.ST_READY:
            return format_html(f"""
<span class="bi bi-check-circle" data-toggle="tooltip" title="{record.ST_LOOKUP[record.state]}" />
            """)
        else:
            return format_html(f"""
<span class="bi bi-hourglass-bottom" data-toggle="tooltip" title="{record.ST_LOOKUP[record.state]}" />
            """)

    def render_button(self, record):
        from container.templatetags.container_buttons import dropdown_start_open
        from ..models import UserCourseBinding
        binding = UserCourseBinding.objects.get(user = record.user, course = record.assignment.course)
        so = dropdown_start_open(binding.coursecontainerbindings(), binding, 'course')
        return format_html(f"""
{self._render_button(record)}&nbsp;/&nbsp;{so}
        """)

    def render_course(self, record):
        return record.assignment.course.name

    def render_assignment(self, record):
        return format_html(f"""
{record.assignment.name}
<input type="hidden" id="assignment-search-{record.id}" value="{record.assignment.search}">
<input type="hidden" id="assignment-match-{record.id}" value=true>
<input type="hidden" id="assignment-isshown-{record.id}" value=true>
        """)

    def render_info(self, record):
        rd = lambda t: t.clocked if t else "Manual"
        return format_html(f"""
<span class="bi bi-arrow-up-right-square-fill" data-toggle="tooltip" title="Submit count">&nbsp;{record.submit_count}</span>
<span class="bi bi-check-square-fill ms-3" data-toggle="tooltip" title="Correction count">&nbsp;{record.correction_count}</span>
        """)

    def render_score(self, record):
        return record.score if record.score else ''



class TableAssignmentConf(tables.Table):
    class Meta:
        model = Assignment
        fields = () 
        sequence = ('meta', 'details', 'dates', 'quota', 'extra_info', 'delete')
        attrs = table_attributes
        empty_text = _("You have not created any assignments yet")

    meta = tables.Column(orderable = False, empty_values = ())
    details = tables.Column(orderable = False, empty_values = ())
    dates = tables.Column(orderable = False, empty_values = ())
    quota = tables.Column(orderable = False, empty_values = ())
    extra_info = tables.Column(orderable = False, empty_values = ())
    delete = tables.Column(orderable = False, empty_values = ())

    def render_meta(self, record):
        return format_html(f"""
<label class="form-check-label" for="a-{record.id}" id="lbl_a-{record.id}" data-toggle="tooltip" title="Course"><i class="bi bi-journal-bookmark-fill"></i>&nbsp;</label>
<span id="a-{record.id}">{record.course.name}</span><br>
<label class="form-check-label mt-1" for="userid-{record.creator.id}" id="lbl_ac-{record.id}" data-toggle="tooltip" title="Creator of this assignment"><i class="bi bi-incognito"></i>&nbsp;</label>
{ru(record.creator)}<br>
<label class="form-check-label mt-1 mb-1" for="cts-{record.id}" id="lbl_ats-{record.id}" data-toggle="tooltip" title="Creation timestamp"><i class="bi bi-clock-history"></i>&nbsp;</label>
<span id="cts-{record.id}">{rd(record.created_at)}</span><br>
{rf(record.folder)}
<input type="hidden" id="assignment-search-{record.id}" value="{record.search}">
<input type="hidden" id="assignment-match-{record.id}" value=true>
<input type="hidden" id="assignment-isshown-{record.id}" value=true>
        """)

    def render_details(self, record):
        return format_html(f"""
<label class="form-check-label align-top" for="name-{record.id}" id="lbl_anm-{record.id}" data-toggle="tooltip" title="Assignment's name"><i class="bi bi-card-heading"></i>&nbsp;</label>
<input class="form-text-input" type="text" id="name-{record.id}" name="name-{record.id}" value="{record.name}" /><br>
<label class="form-check-label align-top mt-2" for="description-{record.id}" id="lbl_dsc-{record.id}" data-toggle="tooltip" title="Assignment's description"><i class="bi bi-journal-richtext"></i>&nbsp;</label>
<textarea class="form-textarea mt-2" id="description-{record.id}" name="description-{record.id}">{record.description}</textarea>
<input type="hidden" id="description-old-{record.id}" name="description-old-{record.id}" value="{record.description}" />
<input type="hidden" id="name-old-{record.id}" name="name-old-{record.id}" value="{record.name}" />
        """)

    def render_dates(self, record):
        rd = lambda t: t.clocked.schedule.clocked_time.strftime("%m/%d/%Y, %H:%M") if t else ""
        d1 = rd(record.task_handout)
        d2 = rd(record.task_collect)
        rd = lambda t: "disabled" if t and t.last_run_at else ""
        st1 = rd(record.task_handout)
        st2 = rd(record.task_collect)
        chk = 'checked' if record.remove_collected else ''
        return format_html(f"""
<div class="container">
  <div class="row">
    <div class="input-group log-event" id="linkedPickers1-{record.id}" data-td-target-input="nearest" data-td-target-toggle="nearest">
      <input id="valid_from-{record.id}" name="valid_from-{record.id}" type="text" class="form-control" data-td-target="#linkedPickers1-{record.id}" {st1}>
      <span class="input-group-text" data-td-target="#linkedPickers1-{record.id}" data-td-toggle="datetimepicker">
        <span class="bi bi-clock"></span>
      </span>
    </div>
  </div>
  <div class="row mt-2">
    <div class="input-group log-event" id="linkedPickers2-{record.id}" data-td-target-input="nearest" data-td-target-toggle="nearest">
      <input id="expires_at-{record.id}" name="expires_at-{record.id}" type="text" class="form-control" data-td-target="#linkedPickers2-{record.id}" {st2}>
      <span class="input-group-text" data-td-target="#linkedPickers2-{record.id}" data-td-toggle="datetimepicker">
        <span class="bi bi-bell"></span>
      </span>
    </div>
  </div>
  <div class="input-group my-2">
    <span class="input-group-text"><span class="bi bi-eraser" data-toggle="tooltip" title="Remove student's assignment folder upon submittion or collection"></span></span>
    <input id="remove_collected-{record.id}" 
       type="checkbox" data-toggle="toggle" name="remove_when_ready"
       data-on="<span class='oi oi-trash'></span>"
       data-off="<span class='bi bi-check-lg'></span>"
       data-onstyle="danger" data-offstyle="secondary" value="{record.remove_collected}" {chk}>
  </div>
</div>
<input type="hidden" id="valid_from-old-{record.id}" value="{d1}" />
<input type="hidden" id="expires_at-old-{record.id}" value="{d2}" />
<input type="hidden" id="remove_collected-old-{record.id}" value="{record.remove_collected}" />
        """)

    def render_extra_info(self, record):
        n = len(UserAssignmentBinding.objects.filter(assignment = record))
        return format_html( f"""<span class="bi bi-box-arrow-in-down-right" data-toggle="tooltip" title="Assignments received or collected so far"></span>&nbsp;{n}""" if n else "" )

    def render_quota(self, record):
        ms = record.max_size if record.max_size else ''
        return format_html(f"""
<label class="form-check-label align-top" for="max_size-{record.id}" id="lbl_frm-{record.id}" data-toggle="tooltip" title="Maximum size of collection folder in MB"><i class="bi bi-box-seam"></i>&nbsp;</label>
<input class="form-text-input" type="text" id="max_size-{record.id}" name="max_size-{record.id}" value="{ms}" size="4" />
<input type="hidden" id="max_size-old-{record.id}" value="{ms}" />
        """)

    def render_delete(self, record):
        return format_html(f"""
<input id="dustbin-{record.id}"
  type="checkbox" data-toggle="toggle" name="selection_delete"
  data-on="<span class='oi oi-trash'></span>"
  data-off="<span class='bi bi-check-lg'></span>"
  data-onstyle="danger" data-offstyle="secondary" value="{record.id}">
        """)


class TableAssignmentHandle(tables.Table):
    class Meta:
        model = UserAssignmentBinding
        fields = ('user', 'score', 'feedback_text')
        sequence = ('button', 'user', 'info', 'score', 'feedback_text')
        attrs = table_attributes
        empty_text = _("This table is still empty")

    button = tables.Column(verbose_name = 'Operation', orderable = False, empty_values = ())
    user = tables.Column(orderable = False, empty_values = (), verbose_name = 'Student')
    info = tables.Column(orderable = False, empty_values = (), verbose_name = 'Info')
    score = tables.Column(orderable = False, empty_values = ())
    feedback_text = tables.Column(orderable = False, empty_values = ())
    

    def render_button(self, record):
        if record.id is None:
            return format_html(f"""
<div class="form-check form-switch">
  <input class="form-check-input" type="checkbox" id="uab-{record.assignment.id}-{record.user.id}" name="selection_createhandout" value="{record.assignment.id}-{record.user.id}" />
  <label class="form-check-label" for="uab-{record.assignment.id}-{record.user.id}" id="lbl_uab-{record.assignment.id}-{record.user.id}"> <span class="bi bi-box-arrow-up-right" data-toggle="tooltip" title="Hand out"></span></label>
</div>
            """)
        elif record.state == record.ST_QUEUED:
            return format_html(f"""
<div class="form-check form-switch">
  <input class="form-check-input" type="checkbox" id="uab-{record.assignment.id}-{record.user.id}" name="selection_handout" value="{record.id}" />
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
        elif record.state in [ record.ST_COLLECTED, record.ST_SUBMITTED ]:
            return format_html(f"""
<div class="form-check form-switch">
  <input class="form-check-input" type="checkbox" id="uab-{record.id}" name="selection_finalize" value="{record.id}" />
  <label class="form-check-label" for="uab-{record.id}" id="lbl_uab-{record.id}"> <span class="bi bi-check-square-fill" data-toggle="tooltip" title="Correct"></span></label>
</div>
            """)
        elif record.state == record.ST_READY:
            return format_html(f"""
<div class="form-check form-switch">
  <input class="form-check-input" type="checkbox" id="uab-{record.id}" name="selection_reassign" value="{record.id}" />
  <label class="form-check-label" for="uab-{record.id}" id="lbl_uab-{record.id}"> <span class="bi bi-recycle" data-toggle="tooltip" title="Reassign"</span></label>
</div>
            """)
        else:
            return format_html(f"""
<span class="bi bi-check-hourglass" data-toggle="tooltip" title="{record.get_state_display()}"></span>
            """)

    def render_user(self, record):
        return format_html(f"""
{ru(record.user)}
<input type="hidden" id="student-search-{record.id}" value="{record.user.profile.search}">
<input type="hidden" id="student-match-{record.id}" value=true>
<input type="hidden" id="student-isshown-{record.id}" value=true>
        """)

    def render_score(self, record):
        s = '' if record.score is None else record.score
        if record.state in [ record.ST_SUBMITTED, record.ST_COLLECTED, record.ST_READY ]:
            return format_html(f"""
<input class="form-text-input" type="text" id="score-{record.id}" name="score" value="{s}" />
<input type="hidden" id="score-old-{record.id}" value="{s}" />
            """)
        else:
            return record.score if record.score else format_html('—')

    def render_feedback_text(self, record):
        t = '' if record.feedback_text is None else record.feedback_text
        if record.state in [ record.ST_SUBMITTED, record.ST_COLLECTED, record.ST_READY ]:
            return format_html(f"""
<textarea class="form-textarea" id="feedback_text-{record.id}" name="feedback_text">{t}</textarea>
<input type="hidden" id="feedback_text-old-{record.id}" value="{t}" />
            """)
        else:
            return record.feedback_text if record.feedback_text else format_html('--')

    def render_info(self, record):
        rd = lambda t: t.clocked if t else "—"
        exp = rd(record.assignment.task_collect)
        return format_html(f"""
Collection due: {exp}<br>
<span class="bi bi-arrow-up-right-square-fill" data-toggle="tooltip" title="Submit count">&nbsp;{record.submit_count}</span>
<span class="bi bi-check-square-fill ms-3" data-toggle="tooltip" title="Correction count">&nbsp;{record.correction_count}</span>
        """)



class TableAssignmentMass(tables.Table):
    class Meta:
        model = Assignment
        fields = ('course', 'name')
        sequence = ('course', 'name', 'group', 'transition', 'handout', 'collect', 'correcting', 'reassign')
        attrs = table_attributes
        empty_text = _("Empty table")

    course = tables.Column(orderable = False)
    name = tables.Column(verbose_name = 'Assignment', orderable = False)
    group = tables.Column(orderable = False, empty_values = ())
    handout = tables.Column(orderable = False, empty_values = ())
    collect = tables.Column(orderable = False, empty_values = ())
    correcting = tables.Column(orderable = False, empty_values = ())
    reassign = tables.Column(orderable = False, empty_values = ())
    transition = tables.Column(orderable = False, empty_values = ())

    def render_course(self, record):
        return format_html(f"""
{record.course.name}<br>{rf(record.folder)}
        """)

    def render_name(self, record):
        return format_html(f"""
{record.name}<br>
<input type="radio" name="assignment_tbl" value="{record.id}-all">&nbsp;all students
<input type="hidden" id="assignment-search-{record.id}" value="{record.search}">
<input type="hidden" id="assignment-match-{record.id}" value=true>
<input type="hidden" id="assignment-isshown-{record.id}" value=true>
        """)

    def render_group(self, record):
        rows = []
        for gid, gn in self.groups[record.course.id]:
            gid = 'n' if gid == -1 else gid
            n = 'FIXME' #len(students)
            radio= f"""<input type="radio" name="assignment_tbl" value="{record.id}-{gid}">"""
            rows.append(f"<div>{radio}&nbsp;{gn} ({n} students)</div>")
        return format_html("<br>".join( rows ))

    def render_transition(self, record):
        rows = []
        for gid, gn in self.groups[record.course.id]:
            n1 = self.get_count(record.id, gid, 'ext')
            n2 = self.get_count(record.id, gid, 'snap')
            rows.append(f"<div data-toggle='tooltip' title='{n1} assignments are being handed out and {n2} are being tarballed'>{n1 + n2}</div>")
        return format_html("<br>".join( rows ))

    def _render_factory(self, record, state, task, icon):
        rows = []
        for gid, gn in self.groups.get(record.course.id, [-1, 'Ungrouped']):
            idx = f'{record.id}-n' if gid is -1 else f'{record.id}-{gid}'
            n = self.get_count(record.id, gid, state)
            d = '' if n else 'disabled'
            rows.append(f"""
<div class="form-check form-switch">
  <input class="form-check-input" type="checkbox" id="{task}-{idx}" name="{task}" value="{idx}" {d}/>
  <label class="form-check-label" for="{task}-{idx}"> <span class="{icon}"> {n}</span></label>
</div>
            """)
        return format_html("<br>".join( rows ))

    def render_handout(self, record):
        return self._render_factory(record, 'qed', 'handout', 'bi bi-box-arrow-up-right')
        
    def render_collect(self, record):
        return self._render_factory(record, 'wip', 'collect', 'bi bi-box-arrow-in-down-right')

    def render_correcting(self, record):
        rows = []
        for gid, gn in self.groups[record.course.id]:
            n1 = self.get_count(record.id, gid, 'sub')
            n2 = self.get_count(record.id, gid, 'col')
            rows.append(f"<div data-toggle='tooltip' title='{n1} assignments are submitted and {n2} are collected'>{n1 + n2}</div>")
        return format_html("<br>".join( rows ))

    def render_reassign(self, record):
        return self._render_factory(record, 'rdy', 'reassign', 'bi bi-recycle')


    def __init__(self, assignments, groups, count):
        super().__init__(assignments)
        self.groups = {}
        for g in groups:
            if g.course.id not in self.groups:
                self.groups[g.course.id] = [(-1, 'Ungrouped')]
            self.groups[g.course.id].append((g.id, g.name))
        for a in assignments:
            if a.course.id not in self.groups:
                self.groups[a.course.id] = [(-1, 'Ungrouped')]
        self._count = count
        self.get_count = lambda assignment_id, group_id, state: self._count.get((assignment_id, group_id, state), 0)


class TableUser(tables.Table):
    user = tables.Column(verbose_name = "Users", order_by = ('user__first_name', 'user__last_name'), orderable = False)

    class Meta:
        model = UserCourseBinding
        fields = ('user',)
        attrs = table_attributes

    def render_user(self, record):
        user = record.user
        prefix = 'B' if record.id else ''
        who = "teacher" if self.is_teacher else "student"
        return format_html(f"""
{ru(user, who)}
<input type="hidden" id="{prefix}{who}-search-{user.id}" value="{user.profile.search}">
<input type="hidden" id="{prefix}{who}-match-{user.id}" value=true>
<input type="hidden" id="{who}-isshown-{user.id}" value=true>
        """)


    def __init__(self, course, user, teacher_selector, bind_table):
        UserCourseBinding.objects.get(course = course, user = user, is_teacher = True) # authorization
        self.is_teacher = teacher_selector
        self.is_bind_table = bind_table
        if bind_table:
            bindings = UserCourseBinding.objects.filter(course = course, is_teacher = self.is_teacher)
        else:
            profiles = user.profile.everybodyelse.exclude(user__in = [ b.user for b in UserCourseBinding.objects.filter(course = course) ])
            bindings = [ UserCourseBinding(user = p.user, course = course, is_teacher = self.is_teacher) for p in profiles ]
        self.prefix = 'teacher' if self.is_teacher else 'student'
        self.Meta.attrs["id"] = f"bind-{self.prefix}" if bind_table else f"users-{self.prefix}"
        super(TableUser, self).__init__(bindings)


class TableGroup(tables.Table):
    class Meta:
        model = CourseGroup
        fields = ('name', 'description',)
        fields = ('button', 'name', 'description',)
        attrs = table_attributes

    button = tables.Column(verbose_name = '', orderable = False, empty_values = ())
    name = tables.Column(orderable = False, empty_values = ())
    description = tables.Column(orderable = False, empty_values = ())

    def render_button(self, record):
        if record.id:
            return format_html(f"""
<input type="checkbox" class="btn-check" name="selection_group_removal" value="{record.id}" id="btn-dg-{record.id}">
<label class="btn btn-outline-danger" for="btn-dg-{record.id}"><i class="bi bi-trash"></i></label>
            """)
        else:
            return format_html("""<button type="button" class="btn btn-success"><i class="bi bi-plus"></i></button>""")

    def render_name(self, record):
        if record.id:
            return format_html(f"""
<input type="hidden" name="group-name" id="group-name-before-{record.id}" value="{record.name}">
<input type="text" name="group-name" id="group-name-after-{record.id}" value="{record.name}">
            """)
        else:
            return format_html(f"""
<input type="text" name="group-name" id="group-name-new-1" value="" placeholder="name a new group">
            """)

    def render_description(self, record):
        if record.id:
            return format_html(f"""
<input type="hidden" name="group-description" id="group-description-before-{record.id}" value="{record.description}">
<textarea name="group-description" id="group-description-after-{record.id}">{record.description}</textarea>
            """)
        else:
            return format_html(f"""
<textarea name="group-description" id="group-description-new-1" placeholder="describe a new group"></textarea>
            """)



