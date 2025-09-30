import json

from django.utils.translation import gettext_lazy as _
from django.utils.safestring import mark_safe
from django.utils.html import format_html
from django.template.loader import render_to_string
from django.db import models
import django_tables2 as tables
from django.contrib.auth.models import User

from education.models import UserCourseBinding, UserAssignmentBinding, Assignment
from hub.templatetags.extras import render_user as ru
from hub.templatetags.extras import render_date as rd
from hub.templatetags.extras import render_folder as rf

from kooplexhub.common import table_attributes


class TableCourse(tables.Table):
    button = tables.TemplateColumn(
        template_name="education/tables/course_attach_toggle.html",
        verbose_name="Attach",
        orderable=False,
        extra_context={"size": "small"}, 
    )

    course = tables.Column(
        verbose_name="Course",
        orderable=False,
    )

    description = tables.Column(
        accessor="course.description",
        verbose_name="Description",
        orderable=False,
    )

    teachers = tables.TemplateColumn(
        template_name="education/tables/course_teachers.html",
        verbose_name="Teachers",
        orderable=False,
    )

    class Meta:
        model = UserCourseBinding
        fields = ("course", ) 
        sequence = ("button", "course", "teachers")
        attrs = table_attributes

    # ---- Factory
    @classmethod
    def from_user(cls, user, **kwargs):
        qs = (
            UserCourseBinding.objects
            .filter(user=user)
            .select_related("course")
            .prefetch_related("course__userbindings__user")
        )
        return cls(qs, **kwargs)
















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
<button type="submit" data-id="{record.id}" data-submit="handin" class="badge rounded-pill bg-warning shadow-sm text-dark p-2 border border-secondary">
  <i class="bi bi-arrow-right-square me-1"></i>Hand in
</button>
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
        return format_html(f'<span data-toggle="tooltip" title="{record.feedback_text}">{record.score}</span>') if record.score else ''


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
        return render_to_string("education/assignment/meta.html", {'assignment': record, 'instance': 'assignment'})

    def render_dates(self, record):
        #FIXME rd = lambda t: t.strftime("%m/%d/%Y, %H:%M") if t else ""
        #FIXME d1 = rd(record.valid_from)
        #FIXME d2 = rd(record.expires_at)
        #FIXME rd = lambda t: "disabled" if t and t.last_run_at else ""
        #FIXME st1 = rd(record.valid_from)
        #FIXME st2 = rd(record.expires_at)
        return render_to_string("education/assignment/dates.html", {'assignment': record})

    def render_manage(self, record):
        return render_to_string("education/assignment/button_handle_all.html", {'assignment': record})

    def render_quota(self, record):
        return render_to_string("education/assignment/quota_and_delete.html", {'assignment': record})

    def render_delete(self, record):
        return render_to_string("education/assignment/dustbin.html", {'assignment': record, 'instance': 'assignment'})



class TableStudentsAndTeachers(tables.Table):
    user=tables.Column(verbose_name = "User", order_by = ('is_teacher', 'user__first_name', 'user__last_name'), orderable = False)
    username=tables.Column(verbose_name = "username", orderable = False, empty_values = ())
    role=tables.Column(verbose_name = "role", orderable = False, empty_values = ())
    class Meta:
        model = UserCourseBinding
        fields = ('user',)
        attrs = table_attributes

    def render_user(self, record):
        return record.user.profile.render_html()

    def render_username(self, record):
        return record.user.username

    def render_role(self, record):
        return "teacher" if record.is_teacher else "student"


