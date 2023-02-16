import os
import json
import datetime
import re
from django import forms
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.contrib.auth.models import User

from kooplexhub.common import tooltip_attrs

from education.models import Assignment, UserCourseBinding, Course, UserAssignmentBinding
from hub.models import Task
from education.filesystem import *

try:
    from kooplexhub.settings import KOOPLEX
except ImportError:
    KOOPLEX = {}
KOOPLEX['kubernetes'].update({})
KOOPLEX['kubernetes']['userdata'].update({})

class dateWidget(forms.DateTimeInput):
    template_name = 'datetime_pick.html'

class FormAssignment(forms.ModelForm):
    class Meta:
        model = Assignment
        fields = [ 'name', 'description', 'remove_collected', 'max_size' ]
        sequence = [ 'folder_assignment', 'name', 'description', 'remove_collected', 'valid_from_widget', 'expires_at_widget', 'max_size' ]
        labels = {
            'name': _('The name of the assignment'),
            'description': _('A short description of the excercises'),
        }

    user = forms.CharField(widget = forms.HiddenInput(), required = True)
    folder_assignment = forms.ChoiceField(
        label = 'Select folder', required = True,
        widget = forms.Select(attrs = tooltip_attrs({
            'title': _('A snapshot will be created of all files in the selected folder, and students will receive a copy of this snapshot.'), 
        }))
    )
    name = forms.CharField(
        label = _("Assignment name"),
        max_length = 200, required = True, 
        widget = forms.TextInput(attrs = tooltip_attrs({ 'title': _('Name your assignment. No worries later you can rename it, just make sure your students do not get confused.') })),
    )
    description = forms.CharField(
        max_length = 100, required = True,
        widget = forms.Textarea(attrs = tooltip_attrs({
            'rows': 3, 
            'title': _('It is always a good idea to have a short but straight to the point abstract of your assignment.'), 
        })),
    )
    # FIXME: add tooltip
    valid_from_widget = forms.DateTimeField(
            label = 'Valid from',
            input_formats = ["%m/%d/%Y, %H:%M"], 
            widget = dateWidget(attrs = { 'icon': 'bi bi-clock', 'name': 'valid_from_widget' }), 
            required = False, 
        )
    # FIXME: add tooltip
    expires_at_widget = forms.DateTimeField(
            label = 'Expires at',
            input_formats = ["%m/%d/%Y, %H:%M"], 
            widget = dateWidget(attrs = { 'icon': 'bi bi-bell', 'name': 'expires_at_widget' }), 
            required = False,
        )
    # FIXME: add tooltip
    remove_collected = forms.BooleanField(
            widget = forms.CheckboxInput(attrs = { 'data-size': 'small', 'data-toggle': 'toggle', 
                'data-on': "<span class='oi oi-trash'></span>", 'data-off': "<span class='bi bi-check-lg'></span>",
                'data-onstyle': "danger", 'data-offstyle': "secondary" }), 
            required = False,
        )
    max_size = forms.IntegerField(
        label = _('Quota [MB]'), required = False,
        widget = forms.NumberInput(attrs = tooltip_attrs({
            'title': _('Total file size quota applied to the assignment.'),
        }))
    )

    def clean(self):
        cleaned_data = super().clean()
        course_id, folder = cleaned_data.pop('folder_assignment').split('---', 1)
        username = cleaned_data.pop('user')
        user = User.objects.get(username = username)
        course = Course.objects.get(id = course_id)
        #authorize
        UserCourseBinding.objects.get(user = user, course = course, is_teacher = True)
        cleaned_data['course'] = course
        cleaned_data['creator'] = user
        cleaned_data['folder'] = folder
        assignmentname = cleaned_data.get('name')
        ve = []
        if not assignmentname:
            ve.append( forms.ValidationError(_(f'Assignment name cannot be empty'), code = 'invalid name') )
        if Assignment.objects.filter(course = course, name = assignmentname):
            ve.append( forms.ValidationError(_(f'Assignment name must be unique'), code = 'invalid name') )
        key = f'{course.name}-{assignmentname}'
        timestamp1 = cleaned_data.pop('valid_from_widget')
        timestamp2 = cleaned_data.pop('expires_at_widget')
        assignment_dummy = Assignment(**cleaned_data)
        # Note, here order matters
        cleaned_data['task_snapshot'] = assignment_dummy._task_snapshot
        cleaned_data['filename'] = assignment_dummy.filename
        if timestamp1:
            cleaned_data['task_handout'] = assignment_dummy._task_handout(timestamp1)
        if timestamp2:
            cleaned_data['task_collect'] = assignment_dummy._task_collect(timestamp2)
        #FIXME: if insane timespan raise an error, < 5 minutes, configurable?
        if timestamp1 and timestamp2 and timestamp1 >= timestamp2:
            ve.append( forms.ValidationError(_(f'Timestamp relation is wrong'), code = 'invalid timestamps') )
        if ve:
            raise forms.ValidationError(ve)
        return cleaned_data


    def __init__(self, *args, **kwargs):
        user = kwargs['initial'].get('user')
        super().__init__(*args, **kwargs)
        #self.fields["creator_id"].value = user.id
        assignment = kwargs.get('instance', Assignment())
        folders = []
        for ucb in UserCourseBinding.objects.filter(user = user, is_teacher = True):
            folders.extend([ (f'{ucb.course.id}---{folder}', f'{ucb.course.name}: {folder}') for folder in ucb.course.dir_assignmentcandidate() ])
        if folders:
            self.okay = True
            self.fields["folder_assignment"].choices = folders
        else:
            self.okay = False


class FormAssignmentConfigure(forms.Form):
    change_log = forms.CharField(widget = forms.HiddenInput(), required = True)

    @staticmethod
    def _parse_timestamp(s):
        p = r'(\d{2})/(\d{2})/(\d{4}), (\d{2}):(\d{2})'
        _, month, day, year, hour, minute, _ = re.split(p, s)
        return timezone.datetime(int(year), int(month), int(day), int(hour), int(minute))

    def __init__(self, *args, **kwargs):
        from . import TableAssignmentConf
        user = kwargs['initial'].get('user')
        assignments = kwargs['initial'].get('assignments')
        super().__init__(*args, **kwargs)
        if assignments:
            self.okay = True
            self.t_assignments = TableAssignmentConf(assignments)
        else:
            self.okay = False

    def clean(self):
        cleaned_data = super().clean()
        ve = []
        details = json.loads(cleaned_data.pop("change_log"))
        userid = details["user_id"]
        delete_ids = details["delete_ids"]
        delete_assignments = list(Assignment.objects.filter(id__in = delete_ids))
        del_timestamps = []
        # authorize, and cleanup tasks
        for assignment in delete_assignments:
            UserCourseBinding.objects.get(user__id = userid, course = assignment.course, is_teacher = True)
            for attr in ["task_snapshot", "task_handout", "task_collect"]:
                tsk = getattr(assignment, attr)
                if tsk:
                    del_timestamps.append(tsk.clocked)
        cleaned_data["delete_assignments"] = delete_assignments
        assignments = []
        timestamps = []
        tasks = []
        for r in details["changes"]:
            assignment_id = r["assignment_id"]
            if assignment_id in delete_ids:
                continue
            assignment = Assignment.objects.get(id = assignment_id)
            # authorize
            UserCourseBinding.objects.get(user__id = userid, course = assignment.course, is_teacher = True)
            # handle trivial attributes
            changed = False
            changes = { i["attribute"]: i["value"] for i in r["changes"] }
            max_size = changes.pop('max_size', None)
            if max_size:
                try:
                    max_size = int(max_size)
                    assert max_size > 0
                except:
                    ve.append( forms.ValidationError(_(f'Wrong value in max_size field'), code = 'invalid quota') )
            for attr in ["name", "description", "max_size", "remove_collected"]:
                value = changes.get(attr, None)
                if value is not None and getattr(assignment, attr) != value:
                    setattr(assignment, attr, value)
                    changed = True
            # handle dates
            valid_from = changes.get('valid_from', None)
            if valid_from == "" and assignment.task_handout:
                del_timestamps.append(assignment.task_handout.clocked)
                assignment.task_handout = None
                changed = True
            elif valid_from:
                try:
                    valid_from = self._parse_timestamp(valid_from)
                    if assignment.task_handout and assignment.task_handout.clocked.clocked_time != valid_from:
                        assignment.task_handout.clocked.clocked_time = valid_from
                        timestamps.append(assignment.task_handout.clocked)
                    else:
                        task = assignment._task_handout(valid_from)
                        assignment.task_handout = task
                        tasks.append(task)
                        changed = True
                except:
                    ve.append( forms.ValidationError(_(f'Wrong value in handout field'), code = 'invalid date') )
            expires_at = changes.get('expires_at', None)
            if expires_at == "" and assignment.task_collect:
                del_timestamps.append(assignment.task_collect.clocked)
                assignment.task_collect = None
                changed = True
            elif expires_at:
                try:
                    expires_at = self._parse_timestamp(expires_at)
                    if assignment.task_collect and assignment.task_collect.clocked.clocked_time != expires_at:
                        assignment.task_collect.clocked.clocked_time = expires_at
                        timestamps.append(assignment.task_collect.clocked)
                    else:
                        task = assignment._task_collect(expires_at)
                        assignment.task_collect = task
                        tasks.append(task)
                        changed = True
                except:
                    ve.append( forms.ValidationError(_(f'Wrong value in collect field'), code = 'invalid date') )
            if changed:
                assignments.append(assignment)
        if ve:
            raise forms.ValidationError(ve)
        if tasks:
            cleaned_data["tasks"] = tasks
        if del_timestamps:
            cleaned_data["delete_timestamps"] = del_timestamps
        if timestamps:
            cleaned_data["timestamps"] = timestamps
        if assignments:
            cleaned_data["assignments"] = assignments
        return cleaned_data


class FormAssignmentHandle(forms.Form):
    change_log = forms.CharField(widget = forms.HiddenInput(), required = True)

    @staticmethod
    def _auth(course, userid):
        UserCourseBinding.objects.get(course = course, user__id = userid, is_teacher = True)

    @staticmethod
    def _helper_many(userid, seq, create = False):
        A = lambda aid: Assignment.objects.get(id = aid)
        S = lambda c, gid: c.groups[None if gid == 'n' else int(gid)]
        many = []
        for code in seq:
            assignment_id, group_id = code.split('-', 1)
            assignment = A(assignment_id)
            FormAssignmentHandle._auth(assignment.course, userid)
            for student in S(assignment.course, group_id):
                created = False
                try:
                    x = UserAssignmentBinding.objects.get(user = student, assignment = assignment)
                except UserAssignmentBinding.DoesNotExist:
                    if create:
                        x = UserAssignmentBinding(user = student, assignment = assignment)
                        created = True
                    else:
                        raise
                many.append((created, x))
        return many

    def clean(self):
        cleaned_data = super().clean()
        details = json.loads(cleaned_data.pop("change_log"))
        userid = details['user_id']
        cleaned_data['handout'] = self._helper_many(userid, details['handoutmany_ids'], create = True)
        cleaned_data['collect'] = self._helper_many(userid, details['collectmany_ids'])
        cleaned_data['reassign'] = self._helper_many(userid, details['reassignmany_ids'])

        # authorize
        A = lambda uab: self._auth(uab.assignment.course, userid)
        cleaned_data['handout'].extend([ (False, uab) for uab in filter(A, UserAssignmentBinding.objects.filter(id__in = details['handout_ids'])) ])
        cleaned_data['collect'].extend(filter(A, UserAssignmentBinding.objects.filter(id__in = details['collect_ids'])))
        cleaned_data['reassign'].extend(filter(A, UserAssignmentBinding.objects.filter(id__in = details['reassign_ids'])))
        cleaned_data['finalize'] = list(filter(A, UserAssignmentBinding.objects.filter(id__in = details['finalize_ids'])))

        A = lambda aid: Assignment.objects.get(id = aid)
        for code in details['create_handout_ids']:
            assignment_id, student_id = code.split('-', 1)
            assignment = A(assignment_id)
            self._auth(assignment.course, userid)
            UserCourseBinding.objects.get(course = course, user__id = student_id, is_teacher = False)
            cleaned_data['handout'].append((True, UserAssignmentBinding(user = User.objects.get(id = student_id), assignment = assignment)))

       # details['meta']

   ##     raise Exception(str(cleaned_data))
        return cleaned_data

    def __init__(self, *args, **kwargs):
        from . import TableAssignmentMass, TableAssignmentHandle
        user = kwargs['initial'].get('user')
        super().__init__(*args, **kwargs)
        courses = [ b.course for b in UserCourseBinding.objects.filter(user = user, is_teacher = True) ]
        assignments = list(Assignment.objects.filter(course__in = courses))
        if not assignments:
            self.okay = False
            return
        self.okay = True
        uabs = list(UserAssignmentBinding.objects.filter(assignment__in = assignments))
        lut_uabs = { a: list(filter(lambda b: b.assignment == a, uabs)) for a in assignments }
        groups = { c: c.groups for c in courses }
        self.t_mass = TableAssignmentMass( assignments, lut_uabs, groups )


class FormAssignmentList(forms.Form):
    submit = forms.CharField(widget = forms.HiddenInput(), required = True)
    def clean(self):
        cleaned_data = super().clean()
        details = json.loads(cleaned_data.pop("submit"))
        userid = details['user_id']
        submit_ids = details['submit_ids']
        cleaned_data['submit'] = UserAssignmentBinding.objects.filter(user__id = userid, id__in = submit_ids, state = UserAssignmentBinding.ST_WORKINPROGRESS)
        return cleaned_data


    def __init__(self, *args, **kwargs):
        from . import TableAssignment
        user = kwargs['initial'].get('user')
        super().__init__(*args, **kwargs)
        courses = [ ucb.course for ucb in UserCourseBinding.objects.filter(user = user, is_teacher = False) ]
        bindings = UserAssignmentBinding.objects.filter(user = user, assignment__course__in = courses)
        if bindings:
            self.okay = True
            self.t_assignment = TableAssignment(bindings)
        else:
            self.okay = False

