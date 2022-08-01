import json

from django.utils.translation import gettext_lazy as _
from django.utils.safestring import mark_safe
from django.utils.html import format_html
from django.db import models
import django_tables2 as tables
from django.contrib.auth.models import User

from ..models import UserCourseBinding, UserAssignmentBinding, Assignment, UserCourseCodeBinding, Group, UserCourseGroupBinding
from hub.templatetags.extras import render_user as ru

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
        #FIXME: order


class TableAssignmentConf(tables.Table):
    class AssignmentSelectionColumn(tables.Column):

        def render(self, record):
            return format_html(f"""
<div class="form-check form-switch">
  <input class="form-check-input" type="checkbox" id="a-{record.id}" name="selection_delete" value="{record.id}" />
</div>
<input type="hidden" name="assignment_ids" value="{record.id}" />
            """)


    def render_course(self, record, column):
        column.attrs = {"td": { "style": "background-color: white"}}
        return format_html(f"""
<p style="font-weight: bold">{record.course.name}</p>
<input type="hidden" name="course" value="{record.course.name}" />
        """)
        return 


    def render_dates(self, record):
        d0 = record.created_at.strftime("%Y-%m-%d %H:%M")
        d1 = record.valid_from.strftime("%Y-%m-%d %H:%M") if record.valid_from else ''
        d2 = record.expires_at.strftime("%Y-%m-%d %H:%M") if record.expires_at else ''
        n = len(UserAssignmentBinding.objects.filter(assignment = record))
        received = f" Assignments received: {n}" if n else ""

        return format_html(f"""
<spam>Created at:</spam>
<div><spam>{d0}</spam></div>

<div class="input-append date" style="margin-top: 5px" id="datetimepicker-valid-{record.id}" date-date="{d1}" data-date-format="yyyy-mm-dd hh:ii">
    Valid from: <input class="datetimepicker span2" size="16" type="text" value="{d1}" name="valid_from-{record.id}">
</div>
<div class="input-append date" style="margin-top: 5px" id="datetimepicker-expiry-{record.id}" date-date="{d2}" data-date-format="yyyy-mm-dd hh:ii">
    Collect at: <input class="datetimepicker span2" size="16" type="text" value="{d2}" name="expires_at-{record.id}">
</div>
<input type="hidden" id="valid_from-old-{record.id}" name="valid_from-old-{record.id}" value="{d1}" />
<input type="hidden" id="expires_at-old-{record.id}" name="expires_at-old-{record.id}" value="{d2}" />
{received}
        """)

    def render_description(self, record):
        return format_html(f"""
<textarea class="form-textarea" id="description-{record.id}" name="description-{record.id}">{record.description}</textarea>
<input type="hidden" id="description-old-{record.id}" name="description-old-{record.id}" value="{record.description}" />
        """)

    def render_name(self, record, column):
        column.attrs = {"td": { "style": "background-color: white"}}
        return format_html(f"""
<div><h6>Assignment name:</h6></div>
<input style="margin-top: -15px" class="form-text-input" type="text" id="name-{record.id}" name="name-{record.id}" value="{record.name}" />
<input type="hidden" id="name-old-{record.id}" name="name-old-{record.id}" value="{record.name}" />
<div>
    <div style="margin-top: 10px">
        <div style="margin-top: 5px"><h6>Folder:</h6></div>
        <div style="margin-top: -8px">{record.folder}</div>
    </div>
<div style="margin-top: 10px">
    <h6>Creator:</h6>
</div> 
<div style="margin-top: -8px">{record.creator.first_name} {record.creator.last_name}</div>
</div>
<div style="margin-top: 10px">
<h6> Assignment description:</h6>
<textarea style="margin-top: -8px" class="form-textarea" id="description-{record.id}" name="description-{record.id}">{record.description}</textarea>
<input type="hidden" id="description-old-{record.id}" name="description-old-{record.id}" value="{record.description}" />
</div>
        """)

    def render_quota(self, record):
        ms = record.max_size if record.max_size else ''
        nf = record.max_number_of_files if record.max_number_of_files else ''
        return format_html(f"""
        <div>
<span>Max size (bytes):</span>
<input class="form-text-input" type="text" id="max_size-{record.id}" name="max_size-{record.id}" value="{ms}" style="width: 30px" />
<input type="hidden" name="max_size-old-{record.id}" value="{ms}" />
</div>
<div style="margin-top: 10px">
<span>Number of files (unit):</span>
<input class="form-text-input" type="text" id="max_number_of_files-{record.id}" name="max_number_of_files-{record.id}" value="{nf}" style="width: 30px" />
<input type="hidden" name="max_number_of_files-old-{record.id}" value="{nf}" />
</div>
        """)

    id = AssignmentSelectionColumn(verbose_name = 'Delete', orderable = False)
    course = tables.Column(orderable = False, empty_values = ())
    name = tables.Column(verbose_name = 'Assignment info', orderable = False)
    description = tables.Column(orderable = False, visible=False)
    dates = tables.Column(verbose_name = 'Assignment dates', orderable = False, empty_values = ())
    quota = tables.Column(orderable = False, empty_values = ())

    
    class Meta:
        model = Assignment
        fields = ('course', 'name', 'description', 'dates', 'quota', 'id')
        attrs = { 
                 "class": "table table-bordered", 
                 "thead": { "class": "thead-dark table-sm" }, 
                 "td": { "style": "padding:.5ex; background-color: white" }, 
                 "th": { "style": "padding:.5ex; background-color: #D3D3D3", "class": "table-secondary" },
                }
        #row_attrs = { 
        #         "class": "search", 
        #         "id": lambda record: f'{record.course.name}-{record.id}'
        #        }
        empty_text = _("You have not created any assignments yet")

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
                 "class": "table table-bordered", 
                 "thead": { "class": "thead-dark table-sm" }, 
                 "td": { "style": "padding:.5ex" }, 
                 "th": { "style": "padding:.5ex", "class": "table-secondary" } 
                }

class TableAssignmentStudentSummary(tables.Table):

    def __init__(self, course):
        import pandas
        from django_pandas.io import read_frame

        bindings = UserAssignmentBinding.objects.filter(assignment__course=course)
        dfm = read_frame(bindings)
        table = dfm.pivot(index="user", columns="assignment", values="score")
        points = dfm.groupby(by="user").agg("sum")[["id"]].rename(columns={"id":"Total points"})
        result = pandas.merge(left=table, right=points, left_on="user", right_on="user", how="inner")
        super().__init__(result)
#        super().__init__(course)
        
def TableCourseStudentSummary(course):

        import pandas
        from django_pandas.io import read_frame

        bindings = UserAssignmentBinding.objects.filter(assignment__course=course)
        if bindings.count() == 0:
            return None
        dfm = read_frame(bindings)
        table = dfm.pivot(index="user", columns="assignment", values="score")
        table.columns = [tc.split("Assignment ")[1].split(" (")[0] for tc in table.columns]
        points = dfm.fillna(0).groupby(by="user").agg("sum")[["score"]].rename(columns={"score":"Total points"})
        result = pandas.merge(left=table, right=points, left_on="user", right_on="user", how="inner")
        header = f"<div style=\"margin-top:10px;\"><h5>{course.name}</h5></div>"
        return format_html(header + result.to_html(classes="table table-bordered table-striped text-center", index_names=False, justify="center", na_rep="-", border=None))


class TableAssignmentHandle(tables.Table):

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
            course = record.assignment.course
            g = UserCourseGroupBinding.objects.get(usercoursebinding__user = record.user, usercoursebinding__course = course).group
            label = f"{course.name} ({g.name})"
        except UserCourseGroupBinding.DoesNotExist:
            label = record.assignment.course.name
        return format_html(f"""
{label}
<input type="hidden" id="course-{record.id}" value="{course.name}" />
        """)

    def render_assignment(self, record):
        return record.assignment.name
    
    def render_user(self, record, column):
        column.attrs = {"td": { "style": "background-color: #D3D3D3"}}
        user = record.user
        return format_html(f"""
{user.first_name} {user.last_name} / {user.username}
<input type="hidden" name="search_student" value="{user.first_name} {user.last_name} {user.username}">
""")

    def render_score(self, record):
        s = record.score if record.score else ''
        if record.state == record.ST_CORRECTED:
            return format_html(f"""
<input class="form-text-input" type="text" id="score-{record.id}" name="score-{record.id}" value="{s}" />
            """)
        elif record.state == record.ST_READY:
            return format_html(f"""
<input class="form-text-input" type="text" id="score-{record.id}" name="score-{record.id}" value="{s}" />
<input type="hidden" name="old_score-{record.id}" value="{s}" />
<input type="hidden" name="ready_ids" value="{record.id}" />
            """)
        else:
            return record.score if record.score else format_html('—')

    def render_feedback_text(self, record):
        t = record.feedback_text if record.feedback_text else ''
        if record.state == record.ST_CORRECTED:
            return format_html(f"""
<textarea class="form-textarea" id="feedback_text-{record.id}" name="feedback_text-{record.id}">{t}</textarea>
<input type="hidden" name="old_feedback_text-{record.id}" value="{t}" />
            """)
        elif record.state == record.ST_READY:
            return format_html(f"""
<textarea class="form-textarea" id="feedback_text-{record.id}" name="feedback_text-{record.id}">{t}</textarea>
<input type="hidden" name="feedback_text-old-{record.id}" value="{t}" />
            """)
        else:
            return t

    id = tables.Column(verbose_name = 'Operation', orderable = False, empty_values = ())
    course = tables.Column(orderable = False, empty_values = (), visible = False)
    assignment = tables.Column(orderable = False, empty_values = (), visible = False)
    user = tables.Column(orderable = False, empty_values = (), verbose_name = 'Student/ username')
    expires_at = tables.Column(orderable = False, empty_values = (), verbose_name = 'Expiry')
    score = tables.Column(orderable = False, empty_values = ())
    feedback_text = tables.Column(orderable = False, empty_values = ())
    submit_count = tables.Column(orderable = False)
    correction_count = tables.Column(orderable = True)
    
    class Meta:
        model = UserAssignmentBinding
        fields = ('id', 'course', 'assignment', 'user', 'expires_at', 'submit_count', 'correction_count', 'score', 'feedback_text')
        attrs = { 
                 "class": "table table-bordered", 
                 "thead": { "class": "thead-dark table-sm" }, 
                 "td": { "style": "padding:.5ex;  background-color: white" }, 
                 "th": { "style": "padding:.5ex; background-color: #D3D3D3", "class": "table-secondary" } 
                }
        empty_text = _("This table is still empty")


    class Meta:
        model = UserAssignmentBinding
        fields = ('id', 'course', 'assignment', 'user', 'expires_at', 'submit_count', 'correction_count', 'score', 'feedback_text')
        attrs = { 
                 "class": "table table-bordered", 
                 "thead": { "class": "thead-dark table-sm" }, 
                 "td": { "style": "padding:.5ex;  background-color: white" }, 
                 "th": { "style": "padding:.5ex; background-color: #D3D3D3", "class": "table-secondary" } 
                }
        empty_text = _("This table is still empty")



class TableAssignmentMass(tables.Table):
    def render_group(self, record):
        return 'Ungrouped' if record is None else record
    def render_handout(self, record):
        idx = 'n' if record is None else record.id
        students = set(self.groups[record]).difference([ b.user for b in self.uab.filter(state__in = [
            UserAssignmentBinding.ST_WORKINPROGRESS,
            UserAssignmentBinding.ST_READY,
            UserAssignmentBinding.ST_SUBMITTED, 
            UserAssignmentBinding.ST_COLLECTED,
            UserAssignmentBinding.ST_CORRECTED
            ]) ])
        n = len(students)
        d = '' if n else 'disabled'
        return format_html(f"""
<div class="form-check form-switch">
  <input class="form-check-input" type="checkbox" id="handout-{idx}" name="handout" value="{idx}" {d}/>
  <label class="form-check-label" for="handout-{idx}"> <span class="bi bi-box-arrow-up-right"> {n}</span></label>
</div>
        """)
    def render_collect(self, record):
        idx = 'n' if record is None else record.id
        students = set(self.groups[record]).intersection([ b.user for b in self.uab.filter(state = UserAssignmentBinding.ST_WORKINPROGRESS) ])
        n = len(students)
        d = '' if n else 'disabled'
        return format_html(f"""
<div class="form-check form-switch">
  <input class="form-check-input" type="checkbox" id="collect-{idx}" name="collect" value="{idx}" {d}/>
  <label class="form-check-label" for="collect-{idx}"> <span class="bi bi-box-arrow-in-down-right"> {n}</span></label>
</div>
        """)
    def render_correct(self, record):
        idx = 'n' if record is None else record.id
        students = set(self.groups[record]).intersection([ b.user for b in self.uab.filter(state__in = [
            UserAssignmentBinding.ST_SUBMITTED, 
            UserAssignmentBinding.ST_COLLECTED
            ]) ])
        n = len(students)
        d = '' if n else 'disabled'
        return format_html(f"""
<div class="form-check form-switch">
  <input class="form-check-input" type="checkbox" id="correct-{idx}" name="correct" value="{idx}" {d}/>
  <label class="form-check-label" for="correct-{idx}"> <span class="bi bi-check-square-fill"> {n}</span></label>
</div>
        """)
    def render_correcting(self, record):
        students = set(self.groups[record]).intersection([ b.user for b in self.uab.filter(state = UserAssignmentBinding.ST_CORRECTED) ])
        n = len(students)
        return format_html(f"<div>{n}</div>")
    def render_reassign(self, record):
        idx = 'n' if record is None else record.id
        students = set(self.groups[record]).intersection([ b.user for b in self.uab.filter(state = UserAssignmentBinding.ST_READY) ])
        n = len(students)
        d = '' if n else 'disabled'
        return format_html(f"""
<div class="form-check form-switch">
  <input class="form-check-input" type="checkbox" id="reassign-{idx}" name="reassign" value="{idx}" {d}/>
  <label class="form-check-label" for="reassign-{idx}"> <span class="bi bi-recycle"> {n}</span></label>
</div>
        """)
    group = tables.Column(orderable = False, empty_values = ())
    handout = tables.Column(orderable = False, empty_values = ())
    collect = tables.Column(orderable = False, empty_values = ())
    correct = tables.Column(orderable = False, empty_values = ())
    correcting = tables.Column(orderable = False, empty_values = ())
    reassign = tables.Column(orderable = False, empty_values = ())
    class Meta:
        attrs = { 
                 "class": "table table-bordered", 
                 "thead": { "class": "thead-dark table-sm" }, 
                 "td": { "style": "padding:.5ex" }, 
                 "th": { "style": "padding:.5ex", "class": "table-secondary" } 
                }
        empty_text = _("Empty table")

    def __init__(self, assignment):
        self.assignment = assignment
        self.groups = assignment.course.groups
        self.uab = UserAssignmentBinding.objects.filter(assignment__id = assignment.id)
        super().__init__(self.groups.keys())


class TableAssignmentMassAll(tables.Table):
    def render_group(self, record):
        rows = []
        for k, v in  self.lut[record.course]:
            gn = 'Ungrouped' if k is None else k.name
            n = len(v)
            rows.append(f"<div>{gn} ({n} students)</div>")
        return format_html("<br>".join( rows ))

    def render_handout(self, record):
        rows = []
        uab = UserAssignmentBinding.objects.filter(assignment__id = record.id)
        for k, v in  self.lut[record.course]:
            idx = f'{record.id}-n' if k is None else f'{record.id}-{k.id}'
            students = set(v).difference([ b.user for b in uab.filter(state__in = [
                UserAssignmentBinding.ST_WORKINPROGRESS,
                UserAssignmentBinding.ST_READY,
                UserAssignmentBinding.ST_SUBMITTED, 
                UserAssignmentBinding.ST_COLLECTED,
                UserAssignmentBinding.ST_CORRECTED
                ]) ])
            n = len(students)
            d = '' if n else 'disabled'
            rows.append(f"""
<div class="form-check form-switch">
  <input class="form-check-input" type="checkbox" id="handout-{idx}" name="handout" value="{idx}" {d}/>
  <label class="form-check-label" for="handout-{idx}"> <span class="bi bi-box-arrow-up-right"> {n}</span></label>
</div>
            """)
        return format_html("<br>".join( rows ))
        
    def render_collect(self, record):
        rows = []
        uab = UserAssignmentBinding.objects.filter(assignment__id = record.id)
        for k, v in  self.lut[record.course]:
            idx = f'{record.id}-n' if k is None else f'{record.id}-{k.id}'
            students = set(v).intersection([ b.user for b in uab.filter(state = UserAssignmentBinding.ST_WORKINPROGRESS) ])
            n = len(students)
            d = '' if n else 'disabled'
            rows.append(f"""
<div class="form-check form-switch">
  <input class="form-check-input" type="checkbox" id="collect-{idx}" name="collect" value="{idx}" {d}/>
  <label class="form-check-label" for="collect-{idx}"> <span class="bi bi-box-arrow-in-down-right"> {n}</span></label>
</div>
            """)
        return format_html("<br>".join( rows ))

    def render_correct(self, record):
        rows = []
        uab = UserAssignmentBinding.objects.filter(assignment__id = record.id)
        for k, v in  self.lut[record.course]:
            idx = f'{record.id}-n' if k is None else f'{record.id}-{k.id}'
            students = set(v).intersection([ b.user for b in uab.filter(state__in = [
                UserAssignmentBinding.ST_SUBMITTED, 
                UserAssignmentBinding.ST_COLLECTED
                ]) ])
            n = len(students)
            d = '' if n else 'disabled'
            rows.append(f"""
<div class="form-check form-switch">
  <input class="form-check-input" type="checkbox" id="correct-{idx}" name="correct" value="{idx}" {d}/>
  <label class="form-check-label" for="correct-{idx}"> <span class="bi bi-check-square-fill"> {n}</span></label>
</div>
            """)
        return format_html("<br>".join( rows ))

    def render_correcting(self, record):
        rows = []
        uab = UserAssignmentBinding.objects.filter(assignment__id = record.id)
        for k, v in  self.lut[record.course]:
            students = set(v).intersection([ b.user for b in uab.filter(state = UserAssignmentBinding.ST_CORRECTED) ])
            n = len(students)
            rows.append(f"<div>{n}</div>")
        return format_html("<br>".join( rows ))

    def render_reassign(self, record):
        rows = []
        uab = UserAssignmentBinding.objects.filter(assignment__id = record.id)
        for k, v in  self.lut[record.course]:
            idx = f'{record.id}-n' if k is None else f'{record.id}-{k.id}'
            students = set(v).intersection([ b.user for b in uab.filter(state = UserAssignmentBinding.ST_READY) ])
            n = len(students)
            d = '' if n else 'disabled'
            rows.append(f"""
<div class="form-check form-switch">
  <input class="form-check-input" type="checkbox" id="reassign-{idx}" name="reassign" value="{idx}" {d}/>
  <label class="form-check-label" for="reassign-{idx}"> <span class="bi bi-recycle"> {n}</span></label>
</div>
            """)
        return format_html("<br>".join( rows ))

    course = tables.Column(orderable = False, empty_values = ())
    group = tables.Column(orderable = False, empty_values = ())
    handout = tables.Column(orderable = False, empty_values = ())
    collect = tables.Column(orderable = False, empty_values = ())
    correcting = tables.Column(orderable = False, empty_values = ())
    correct = tables.Column(orderable = False, empty_values = ())
    reassign = tables.Column(orderable = False, empty_values = ())

    class Meta:
        model = Assignment
        fields = ('course', 'name', 'group', 'handout', 'collect', 'correct', 'correcting', 'reassign')
        attrs = { 
                 "class": "table table-bordered", 
                 "thead": { "class": "thead-dark table-sm" }, 
                 "td": { "style": "padding:.5ex" }, 
                 "th": { "style": "padding:.5ex", "class": "table-secondary" } 
                }
        empty_text = _("Empty table")

    def __init__(self, qs):
        super().__init__(qs)
        courses = set([ a.course for a in qs ])
        self.lut = { c: list(c.groups.items()) for c in courses }


class TableUser(tables.Table):
    user = tables.Column(verbose_name = "Users", order_by = ('user__first_name', 'user__last_name'), orderable = False)

    class Meta:
        model = UserCourseBinding
        fields = ('user',)
        attrs = {
                 "class": "table table-bordered",
                 "thead": { "class": "thead-dark table-sm" },
                 "td": { "class": "p-1" },
                 "th": { "class": "table-secondary p-1" }
                }

    def render_user(self, record):
        user = record.user
        hidden = f"""
<input type="hidden" name="{self.prefix}-binding_id" value="{record.id}">
        """ if record.id else f"""
<input type="hidden" name="{self.prefix}-user_id" value="{record.user.id}">
        """
        prefix = '' if record.id else '_'
        who = "teacher" if self.is_teacher else "student"
        return format_html(f"""
{ru(user, who)}
<input type="hidden" id="search-{who}-{user.id}" value="{user.username} {user.first_name} {user.last_name} {user.first_name}">
<input type="hidden" name="{prefix}{who}-ids" value="{user.id}">
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

#class TableUser(tables.Table):
#    def render_id(self, record):
#        f = 'teacher' if self.teacher_selector else 'student'
#        try:
#            ucb = UserCourseBinding.objects.get(course = self.course, user = record, is_teacher = self.teacher_selector)
#            return format_html(f"""
#<div class="form-check col-sm form-switch">
#  <input class="form-check-input" type="checkbox" id="ur-{ucb.id}" name="keep_bid" value="{ucb.id}" checked />
#  <input type="hidden" id="ur-orig-{ucb.id}" name="bound_bid" value="{ucb.id}" />
#  <label class="form-check-label" for="ur-{ucb.id}" id="lbl_ur-{ucb.id}"> Added</label>
#</div>
#            """)
#        except UserCourseBinding.DoesNotExist:
#            return format_html(f"""
#<div class="form-check col-sm form-switch">
#  <input class="form-check-input" type="checkbox" id="u-{f}-{record.id}" name="add_uid" value="{record.id}" />
#  <label class="form-check-label" for="u-{f}-{record.id}" id="lbl_u-{f}-{record.id}"> Skip</label>
#</div>
#
#            """)
#
#    def render_name(self, record):
#        user = record
#        return format_html(f"""
#<span data-toggle="tooltip" title="username: {record.username}\nemail: {record.email}"><i class="bi bi-info-square-fill" ></i>&nbsp;{record.first_name} <b>{record.last_name}</b></span>
#<input type="hidden" name="search_studenttwo" value="{user.first_name} {user.last_name} {user.username}">
#<input type="hidden" name="search_student" value="{user.first_name} {user.last_name} {user.username}">
#        """)
#
#    def render_course(self, record):
#        return format_html(", ".join([ ucb.course.name for ucb in UserCourseBinding.objects.filter(user = record) ]))
#
#    def render_coursecode(self, record):
#        return ", ".join([ ucb.coursecode.courseid for ucb in UserCourseCodeBinding.objects.filter(user = record) ])
#
#    id = tables.Column(verbose_name = 'Operation', orderable = False)
#    name = tables.Column(orderable = False, empty_values = ())
#    course = tables.Column(orderable = False, empty_values = ())
#    #coursecode = tables.Column(orderable = False, empty_values = ())
#
#    class Meta:
#        model = User
#        fields = ('id', 'name', 'course')#, 'coursecode')
#        attrs = { 
#                 "class": "table table-striped table-bordered", 
#                 "thead": { "class": "thead-dark table-sm" }, 
#                 "td": { "style": "padding:.5ex" }, 
#                 "th": { "style": "padding:.5ex", "class": "table-secondary" } 
#                }
#
#    def __init__(self, course, teacher_selector, *args, **kwargs):
#        complementary_users = [ ucb.user.username for ucb in UserCourseBinding.objects.filter(course = course, is_teacher = not teacher_selector) ]
#        users = User.objects.all().exclude(username__in = KOOPLEX.get('blacklist', ['hubadmin', 'admin'])).exclude(username__in = complementary_users)
#        super(TableUser, self).__init__(users)
#        self.course = course
#        self.teacher_selector = teacher_selector
#        self.empty = len(users) == 0


class TableGroup(tables.Table):
    class Meta:
        model = Group
        fields = ('course', 'name', 'description',)
        fields = ('button', 'course', 'name', 'description',)
        attrs = { 
                 "class": "table table-striped table-bordered mt-3", 
                 "thead": { "class": "thead-dark table-sm" }, 
                 "td": { "class": "p-1" }, 
                 "th": { "class": "table-secondary p-1" } 
                }
    button = tables.Column(verbose_name = 'Delete', orderable = False, empty_values = ())
    course = tables.Column(orderable = False, empty_values = ())
    name = tables.Column(orderable = False, empty_values = ())
    description = tables.Column(orderable = False, empty_values = ())

    def render_button(self, record):
        return format_html(f"""
<input type="checkbox" class="btn-check" name="selection_group_removal" value="{record.id}" id="btn-dg-{record.id}">
<label class="btn btn-outline-danger" for="btn-dg-{record.id}"><i class="bi bi-trash"></i></label>
        """)

    def render_name(self, record):
        return format_html(f"""
<input type="hidden" name="group-name-before-{record.id}" value="{record.name}">
<input type="text" name="group-name-after-{record.id}" value="{record.name}">
        """)

    def render_description(self, record):
        return format_html(f"""
<input type="hidden" name="group-description-before-{record.id}" value="{record.description}">
<textarea name="group-description-after-{record.id}">{record.description}</textarea>
        """)



