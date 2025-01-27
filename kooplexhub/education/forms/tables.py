import json

from django.utils.translation import gettext_lazy as _
from django.utils.safestring import mark_safe
from django.utils.html import format_html
from django.template.loader import render_to_string
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
ta_light.update({ "td": { "class": "p-1 text-secondary" } })

class TableAssignment(tables.Table):
    class Meta:
        model = UserAssignmentBinding
        fields = ('assignment', 'score')
        sequence = ('button', 'assignment', 'score')
        attrs = ta_light

    button = tables.Column(verbose_name = '', orderable = False, empty_values = ())
    assignment = tables.Column(orderable = False)
    score = tables.Column(orderable = False, empty_values = ())

    def render_button(self, record):
        if record.state == record.ST_WORKINPROGRESS:
            return format_html(f"""
<div class="form-check form-switch">
  <input class="form-check-input" type="checkbox" name="userassignmentbinding_ids" name="selection" value="{record.id}" data-course="{record.assignment.course.id}" />
</div>
            """)
        elif record.state == record.ST_COLLECTED:
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


    def render_assignment(self, record):
        return format_html(f"""
<span data-toggle="tooltip" title="Submit count: {record.submit_count}\nCorrection count: {record.correction_count}">
{record.assignment.name}
</span>
<input type="hidden" id="assignment-search-{record.id}" value="{record.assignment.search}">
<input type="hidden" id="assignment-match-{record.id}" value=true>
<input type="hidden" id="assignment-isshown-{record.id}" value=true>
        """)


    def render_score(self, record):
        return format_html(f'<span data-toggle="tooltip" title="{record.feedback_text}">record.score</span>') if record.score else ''


class TableAssignmentConf(tables.Table):
    class Meta:
        model = Assignment
        fields = () 
        sequence = ('details', 'manage', 'dates', 'quota', 'delete')
        attrs = table_attributes
        empty_text = _("You have not created any assignments yet")

    details = tables.Column(orderable = False, empty_values = ())
    dates = tables.Column(orderable = False, empty_values = ())
    quota = tables.Column(orderable = False, empty_values = ())
    manage = tables.Column(orderable = False, empty_values = ())
    delete = tables.Column(orderable = False, empty_values = ())

    def __init__(self, data, exclude_columns=None, *args, **kwargs):
        super().__init__(data, *args, **kwargs)

        # Exclude columns dynamically if provided
        if exclude_columns:
            for column in exclude_columns:
                if column in self.base_columns:
                    self.columns.hide(column)
        # FIXME: until refactored don't show quota
        self.columns.hide('quota')

    def render_details(self, record):
        return render_to_string("widgets/assignment_conf_meta.html", {'assignment': record, 'instance': 'assignment'})

    def render_dates(self, record):
        #FIXME rd = lambda t: t.strftime("%m/%d/%Y, %H:%M") if t else ""
        #FIXME d1 = rd(record.valid_from)
        #FIXME d2 = rd(record.expires_at)
        #FIXME rd = lambda t: "disabled" if t and t.last_run_at else ""
        #FIXME st1 = rd(record.valid_from)
        #FIXME st2 = rd(record.expires_at)
        return render_to_string("widgets/assignment_conf_dates.html", {'assignment': record})

    def render_manage(self, record):
        return render_to_string("widgets/assignment_conf_handlerbuttons.html", {'assignment': record})


    def render_quota(self, record):
        return render_to_string("widgets/assignment_conf_quotaanddelete.html", {'assignment': record})


    def render_delete(self, record):
        return render_to_string("widgets/assignment_conf_dustbin.html", {'assignment': record, 'instance': 'assignment'})




#DEPRECATE
#class TableAssignmentMass(tables.Table):
#    class Meta:
#        model = Assignment
#        fields = ('course', 'name')
#        sequence = ('course', 'name', 'group', 'transition', 'handout', 'collect', 'correcting', 'reassign')
#        attrs = table_attributes
#        empty_text = _("Empty table")
#
#    course = tables.Column(orderable = False)
#    name = tables.Column(verbose_name = 'Assignment', orderable = False)
#    group = tables.Column(orderable = False, empty_values = ())
#    handout = tables.Column(orderable = False, empty_values = ())
#    collect = tables.Column(orderable = False, empty_values = ())
#    correcting = tables.Column(orderable = False, empty_values = ())
#    reassign = tables.Column(orderable = False, empty_values = ())
#    transition = tables.Column(orderable = False, empty_values = ())
#
#    def render_course(self, record):
#        return format_html(f"""
#{record.course.name}<br>{rf(record.folder)}
#        """)
#
#    def render_name(self, record):
#        return format_html(f"""
#{record.name}<br>
#<input type="radio" name="assignment_tbl" value="{record.id}-all">&nbsp;all students
#<input type="hidden" id="assignment-search-{record.id}" value="{record.search}">
#<input type="hidden" id="assignment-match-{record.id}" value=true>
#<input type="hidden" id="assignment-isshown-{record.id}" value=true>
#        """)
#
#    def render_group(self, record):
#        rows = []
#        for gid, gn in self.groups[record.course.id]:
#            gid = 'n' if gid == -1 else gid
#            n = 'FIXME' #len(students)
#            radio= f"""<input type="radio" name="assignment_tbl" value="{record.id}-{gid}">"""
#            rows.append(f"<div>{radio}&nbsp;{gn} ({n} students)</div>")
#        return format_html("<br>".join( rows ))
#
#    def render_transition(self, record):
#        rows = []
#        for gid, gn in self.groups[record.course.id]:
#            n1 = self.get_count(record.id, gid, 'ext')
#            n2 = self.get_count(record.id, gid, 'snap')
#            rows.append(f"<div data-toggle='tooltip' title='{n1} assignments are being handed out and {n2} are being tarballed'>{n1 + n2}</div>")
#        return format_html("<br>".join( rows ))
#
#    def _render_factory(self, record, state, task, icon):
#        rows = []
#        for gid, gn in self.groups.get(record.course.id, [-1, 'Ungrouped']):
#            idx = f'{record.id}-n' if gid is -1 else f'{record.id}-{gid}'
#            n = self.get_count(record.id, gid, state)
#            d = '' if n else 'disabled'
#            rows.append(f"""
#<div class="form-check form-switch">
#  <input class="form-check-input" type="checkbox" id="{task}-{idx}" name="{task}" value="{idx}" {d}/>
#  <label class="form-check-label" for="{task}-{idx}"> <span class="{icon}"> {n}</span></label>
#</div>
#            """)
#        return format_html("<br>".join( rows ))
#
#    def render_handout(self, record):
#        return self._render_factory(record, 'qed', 'handout', 'bi bi-box-arrow-up-right')
#        
#    def render_collect(self, record):
#        return self._render_factory(record, 'wip', 'collect', 'bi bi-box-arrow-in-down-right')
#
#    def render_correcting(self, record):
#        rows = []
#        for gid, gn in self.groups[record.course.id]:
#            n1 = self.get_count(record.id, gid, 'sub')
#            n2 = self.get_count(record.id, gid, 'col')
#            rows.append(f"<div data-toggle='tooltip' title='{n1} assignments are submitted and {n2} are collected'>{n1 + n2}</div>")
#        return format_html("<br>".join( rows ))
#
#    def render_reassign(self, record):
#        return self._render_factory(record, 'rdy', 'reassign', 'bi bi-recycle')
#
#
#    def __init__(self, assignments, groups, count):
#        super().__init__(assignments)
#        self.groups = {}
#        for g in groups:
#            if g.course.id not in self.groups:
#                self.groups[g.course.id] = [(-1, 'Ungrouped')]
#            self.groups[g.course.id].append((g.id, g.name))
#        for a in assignments:
#            if a.course.id not in self.groups:
#                self.groups[a.course.id] = [(-1, 'Ungrouped')]
#        self._count = count
#        self.get_count = lambda assignment_id, group_id, state: self._count.get((assignment_id, group_id, state), 0)


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



