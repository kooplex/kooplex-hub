import os
import json
import datetime
from django import forms
from django.utils.translation import gettext_lazy as _

from django.contrib.auth.models import User
from django_celery_beat.models import ClockedSchedule, PeriodicTask

from kooplexhub.common import tooltip_attrs

from education.models import Assignment, UserCourseBinding, Course
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
        schedule_now = ClockedSchedule(clocked_time = datetime.datetime.now())
        timestamp1 = cleaned_data.pop('valid_from_widget')
        timestamp2 = cleaned_data.pop('expires_at_widget')
        assignment_dummy = Assignment(**cleaned_data)
        filename = os.path.join(course_assignment_snapshot(course), f'assignment-snapshot-{assignment_dummy.safename}.{time.time()}.tar.gz')
        cleaned_data['filename'] = filename
        cleaned_data['task_snapshot'] = PeriodicTask(
            name = f"create_assignment_{key}",
            task = "kooplexhub.tasks.create_tar",
            clocked = schedule_now,
            one_off = True,
            kwargs = json.dumps({
                'folder': assignment_source(assignment_dummy),
                'tarbal': filename,
            })
        )
        if timestamp1:
            schedule = ClockedSchedule(clocked_time = timestamp1)
            cleaned_data['task_handout'] = PeriodicTask(
                name = f"handout_{key}",
                task = "education.tasks.assignment_handout",
                clocked = schedule,
                one_off = True,
                kwargs = json.dumps({
                    'course_id': course.id,
                    'assignment_folder': folder,
                })
            )
        if timestamp2:
            schedule = ClockedSchedule.objects.create(clocked_time = timestamp2)
            cleaned_data['task_collect'] = PeriodicTask(
                name = f"collect_{key}",
                task = "education.tasks.assignment_collect",
                clocked = schedule,
                one_off = True,
                kwargs = json.dumps({
                    'course_id': course.id,
                    'assignment_folder': folder,
                })
            )
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
        #raise Exception(str(cleaned_data))
        details = json.loads(cleaned_data.pop("change_log"))
        userid = details["user_id"]
        delete_ids = list(map(lambda i: int(i), details["delete_ids"]))
        delete_assignments = list(Assignment.objects.filter(id__in = delete_ids))
        # authorize
        for assignment in delete_assignments:
            UserCourseBinding.objects.get(user__id = userid, course = assignment.course, is_teacher = True)
        cleaned_data["delete_assignments"] = delete_assignments
        update = []
        for r in details["changes"]:
            assignment_id = r["assignment_id"]
            if assignment_id in delete_ids:
                continue
            assignment = Assignment.objects.get(id = assignment_id)
            # authorize
            UserCourseBinding.objects.get(user__id = userid, course = assignment.course, is_teacher = True)
            changed = False
            for c in r["changes"]:
                attr = c["attribute"]
                if hasattr(assignment, attr):
                    setattr(assignment, attr, c["value"])
                    changed = True
            if changed:
                update.append(assignment)
        if update:
            cleaned_data["assignments"] = update
        return cleaned_data

