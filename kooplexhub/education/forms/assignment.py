from django import forms


class AssignmentScheduleForm(forms.Form):
    field = forms.ChoiceField(
        choices=(
            ("valid_from", "Valid from"),
            ("expires_at", "Expires at"),
        )
    )

    valid_from = forms.DateTimeField(
        required=False,
        input_formats=[
            "%Y-%m-%dT%H:%M",
        ],
    )

    expires_at = forms.DateTimeField(
        required=False,
        input_formats=[
            "%Y-%m-%dT%H:%M",
        ],
    )


#FIXME:  import os
#FIXME:  import json
#FIXME:  import datetime
#FIXME:  import re
#FIXME:  from django import forms
#FIXME:  from django.utils.translation import gettext_lazy as _
#FIXME:  from django.utils import timezone
#FIXME:  from django.contrib.auth.models import User
#FIXME:  import pandas
#FIXME:  from django_pandas.io import read_frame
#FIXME:  
#FIXME:  from kooplexhub.common import tooltip_attrs
#FIXME:  
#FIXME:  from education.models import Assignment, UserCourseBinding, Course, UserAssignmentBinding#, UserCourseGroupBinding, CourseGroup
#FIXME:  from education.fs import *
#FIXME:  
#FIXME:  
#FIXME:  class dateWidget(forms.DateTimeInput):
#FIXME:      template_name = 'datetime_pick.html'
#FIXME:  
#FIXME:  class FormAssignment(forms.ModelForm):
#FIXME:      class Meta:
#FIXME:          model = Assignment
#FIXME:          fields = [ 'name', 'description', 'remove_collected', 'max_size' ]
#FIXME:          sequence = [ 'folder_assignment', 'name', 'description', 'remove_collected', 'valid_from_widget', 'expires_at_widget', 'max_size' ]
#FIXME:          labels = {
#FIXME:              'name': _('The name of the assignment'),
#FIXME:              'description': _('A short description of the excercises'),
#FIXME:          }
#FIXME:  
#FIXME:      user = forms.CharField(widget = forms.HiddenInput(), required = True)
#FIXME:      folder_assignment = forms.ChoiceField(
#FIXME:          label = 'Select folder', required = True,
#FIXME:          widget = forms.Select(attrs = tooltip_attrs({
#FIXME:              'title': _('A snapshot will be created of all files in the selected folder, and students will receive a copy of this snapshot.'), 
#FIXME:          }))
#FIXME:      )
#FIXME:      name = forms.CharField(
#FIXME:          label = _("Assignment name"),
#FIXME:          max_length = 200, required = True, 
#FIXME:          widget = forms.TextInput(attrs = tooltip_attrs({ 'title': _('Name your assignment. No worries later you can rename it, just make sure your students do not get confused.') })),
#FIXME:      )
#FIXME:      description = forms.CharField(
#FIXME:          max_length = 100, required = True,
#FIXME:          widget = forms.Textarea(attrs = tooltip_attrs({
#FIXME:              'rows': 3, 
#FIXME:              'title': _('It is always a good idea to have a short but straight to the point abstract of your assignment.'), 
#FIXME:          })),
#FIXME:      )
#FIXME:      # FIXME: add tooltip
#FIXME:      valid_from_widget = forms.DateTimeField(
#FIXME:              label = 'Valid from',
#FIXME:              input_formats = ["%m/%d/%Y, %H:%M"], 
#FIXME:              widget = dateWidget(attrs = { 'icon': 'bi bi-clock', 'name': 'valid_from_widget' }), 
#FIXME:              required = False, 
#FIXME:          )
#FIXME:      # FIXME: add tooltip
#FIXME:      expires_at_widget = forms.DateTimeField(
#FIXME:              label = 'Expires at',
#FIXME:              input_formats = ["%m/%d/%Y, %H:%M"], 
#FIXME:              widget = dateWidget(attrs = { 'icon': 'bi bi-bell', 'name': 'expires_at_widget' }), 
#FIXME:              required = False,
#FIXME:          )
#FIXME:      # FIXME: add tooltip
#FIXME:      remove_collected = forms.BooleanField(
#FIXME:              widget = forms.CheckboxInput(attrs = { 'data-size': 'small', 'data-toggle': 'toggle', 
#FIXME:                  'data-on': "<span class='oi oi-trash'></span>", 'data-off': "<span class='bi bi-check-lg'></span>",
#FIXME:                  'data-onstyle': "danger", 'data-offstyle': "secondary" }), 
#FIXME:              required = False,
#FIXME:          )
#FIXME:      max_size = forms.IntegerField(
#FIXME:          label = _('Quota [MB]'), required = False,
#FIXME:          widget = forms.NumberInput(attrs = tooltip_attrs({
#FIXME:              'title': _('Total file size quota applied to the assignment.'),
#FIXME:          }))
#FIXME:      )
#FIXME:  
#FIXME:      def clean(self):
#FIXME:          cleaned_data = super().clean()
#FIXME:          course_id, folder = cleaned_data.pop('folder_assignment').split('---', 1)
#FIXME:          username = cleaned_data.pop('user')
#FIXME:          user = User.objects.get(username = username)
#FIXME:          course = Course.objects.get(id = course_id)
#FIXME:          #authorize
#FIXME:          UserCourseBinding.objects.get(user = user, course = course, is_teacher = True)
#FIXME:          cleaned_data['course'] = course
#FIXME:          cleaned_data['creator'] = user
#FIXME:          cleaned_data['folder'] = folder
#FIXME:          assignmentname = cleaned_data.get('name')
#FIXME:          ve = []
#FIXME:          if not assignmentname:
#FIXME:              ve.append( forms.ValidationError(_(f'Assignment name cannot be empty'), code = 'invalid name') )
#FIXME:          if Assignment.objects.filter(course = course, name = assignmentname):
#FIXME:              ve.append( forms.ValidationError(_(f'Assignment name must be unique'), code = 'invalid name') )
#FIXME:          key = f'{course.name}-{assignmentname}'
#FIXME:          timestamp1 = cleaned_data.pop('valid_from_widget')
#FIXME:          timestamp2 = cleaned_data.pop('expires_at_widget')
#FIXME:          assignment_dummy = Assignment(**cleaned_data)
#FIXME:          # Note, here order matters
#FIXME:          cleaned_data['task_snapshot'] = assignment_dummy._task_snapshot
#FIXME:          cleaned_data['filename'] = assignment_dummy.filename
#FIXME:          if timestamp1:
#FIXME:              cleaned_data['task_handout'] = assignment_dummy._task_handout(timestamp1)
#FIXME:          if timestamp2:
#FIXME:              cleaned_data['task_collect'] = assignment_dummy._task_collect(timestamp2)
#FIXME:          #FIXME: if insane timespan raise an error, < 5 minutes, configurable?
#FIXME:          if timestamp1 and timestamp2 and timestamp1 >= timestamp2:
#FIXME:              ve.append( forms.ValidationError(_(f'Timestamp relation is wrong'), code = 'invalid timestamps') )
#FIXME:          if ve:
#FIXME:              raise forms.ValidationError(ve)
#FIXME:          return cleaned_data
#FIXME:  
#FIXME:  
#FIXME:      def __init__(self, *args, **kwargs):
#FIXME:          user = kwargs['initial'].get('user')
#FIXME:          self.pk = kwargs.pop('pk', None)
#FIXME:          super().__init__(*args, **kwargs)
#FIXME:          #self.fields["creator_id"].value = user.id
#FIXME:          assignment = kwargs.get('instance', Assignment())
#FIXME:          folders = []
#FIXME:          q=UserCourseBinding.objects.filter(user=user, course_id=self.pk, is_teacher=True) if self.pk else UserCourseBinding.objects.filter(user=user, is_teacher=True)
#FIXME:          for ucb in q:
#FIXME:              try:
#FIXME:                  folders.extend([ (f'{ucb.course.id}---{folder}', f'{ucb.course.name}: {folder}') for folder in ucb.course.dir_assignmentcandidate() ])
#FIXME:              except:
#FIXME:                  pass
#FIXME:          if folders:
#FIXME:              self.okay = True
#FIXME:              self.fields["folder_assignment"].choices = folders
#FIXME:          else:
#FIXME:              self.okay = False
#FIXME:  
#FIXME:  
#FIXME:  class FormAssignmentConfigure(forms.Form):
#FIXME:      change_log = forms.CharField(widget = forms.HiddenInput(), required = True)
#FIXME:  
#FIXME:      @staticmethod
#FIXME:      def _parse_timestamp(s):
#FIXME:          p = r'(\d{2})/(\d{2})/(\d{4}), (\d{2}):(\d{2})'
#FIXME:          _, month, day, year, hour, minute, _ = re.split(p, s)
#FIXME:          return timezone.datetime(int(year), int(month), int(day), int(hour), int(minute))
#FIXME:  
#FIXME:      def __init__(self, *args, **kwargs):
#FIXME:          from . import TableAssignmentConf
#FIXME:          user = kwargs['initial'].get('user')
#FIXME:          assignments = kwargs['initial'].get('assignments')
#FIXME:          super().__init__(*args, **kwargs)
#FIXME:          if assignments:
#FIXME:              self.okay = True
#FIXME:              self.t_assignments = TableAssignmentConf(assignments)
#FIXME:          else:
#FIXME:              self.okay = False
#FIXME:  
#FIXME:      def clean(self):
#FIXME:          cleaned_data = super().clean()
#FIXME:          ve = []
#FIXME:          details = json.loads(cleaned_data.pop("change_log"))
#FIXME:          userid = details["user_id"]
#FIXME:          delete_ids = details["delete_ids"]
#FIXME:          delete_assignments = list(Assignment.objects.filter(id__in = delete_ids))
#FIXME:          del_timestamps = []
#FIXME:          # authorize, and cleanup tasks
#FIXME:          for assignment in delete_assignments:
#FIXME:              UserCourseBinding.objects.get(user__id = userid, course = assignment.course, is_teacher = True)
#FIXME:              for attr in ["task_snapshot", "task_handout", "task_collect"]:
#FIXME:                  tsk = getattr(assignment, attr)
#FIXME:                  if tsk:
#FIXME:                      del_timestamps.append(tsk.clocked)
#FIXME:          cleaned_data["delete_assignments"] = delete_assignments
#FIXME:          assignments = []
#FIXME:          timestamps = []
#FIXME:          tasks = []
#FIXME:          for r in details["changes"]:
#FIXME:              assignment_id = r["assignment_id"]
#FIXME:              if assignment_id in delete_ids:
#FIXME:                  continue
#FIXME:              assignment = Assignment.objects.get(id = assignment_id)
#FIXME:              # authorize
#FIXME:              UserCourseBinding.objects.get(user__id = userid, course = assignment.course, is_teacher = True)
#FIXME:              # handle trivial attributes
#FIXME:              changed = False
#FIXME:              changes = { i["attribute"]: i["value"] for i in r["changes"] }
#FIXME:              max_size = changes.pop('max_size', None)
#FIXME:              if max_size:
#FIXME:                  try:
#FIXME:                      max_size = int(max_size)
#FIXME:                      assert max_size > 0
#FIXME:                  except:
#FIXME:                      ve.append( forms.ValidationError(_(f'Wrong value in max_size field'), code = 'invalid quota') )
#FIXME:              for attr in ["name", "description", "max_size", "remove_collected"]:
#FIXME:                  value = changes.get(attr, None)
#FIXME:                  if value is not None and getattr(assignment, attr) != value:
#FIXME:                      setattr(assignment, attr, value)
#FIXME:                      changed = True
#FIXME:              # handle dates
#FIXME:              valid_from = changes.get('valid_from', None)
#FIXME:              if valid_from == "" and assignment.task_handout:
#FIXME:                  del_timestamps.append(assignment.task_handout.clocked)
#FIXME:                  assignment.task_handout = None
#FIXME:                  changed = True
#FIXME:              elif valid_from:
#FIXME:                  try:
#FIXME:                      valid_from = self._parse_timestamp(valid_from)
#FIXME:                      if assignment.task_handout and assignment.task_handout.clocked.clocked_time != valid_from:
#FIXME:                          assignment.task_handout.clocked.clocked_time = valid_from
#FIXME:                          timestamps.append(assignment.task_handout.clocked)
#FIXME:                      else:
#FIXME:                          task = assignment._task_handout(valid_from)
#FIXME:                          assignment.task_handout = task
#FIXME:                          tasks.append(task)
#FIXME:                          changed = True
#FIXME:                  except:
#FIXME:                      ve.append( forms.ValidationError(_(f'Wrong value in handout field'), code = 'invalid date') )
#FIXME:              expires_at = changes.get('expires_at', None)
#FIXME:              if expires_at == "" and assignment.task_collect:
#FIXME:                  del_timestamps.append(assignment.task_collect.clocked)
#FIXME:                  assignment.task_collect = None
#FIXME:                  changed = True
#FIXME:              elif expires_at:
#FIXME:                  try:
#FIXME:                      expires_at = self._parse_timestamp(expires_at)
#FIXME:                      if assignment.task_collect and assignment.task_collect.clocked.clocked_time != expires_at:
#FIXME:                          assignment.task_collect.clocked.clocked_time = expires_at
#FIXME:                          timestamps.append(assignment.task_collect.clocked)
#FIXME:                      else:
#FIXME:                          task = assignment._task_collect(expires_at)
#FIXME:                          assignment.task_collect = task
#FIXME:                          tasks.append(task)
#FIXME:                          changed = True
#FIXME:                  except:
#FIXME:                      ve.append( forms.ValidationError(_(f'Wrong value in collect field'), code = 'invalid date') )
#FIXME:              if changed:
#FIXME:                  assignments.append(assignment)
#FIXME:          if ve:
#FIXME:              raise forms.ValidationError(ve)
#FIXME:          if tasks:
#FIXME:              cleaned_data["tasks"] = tasks
#FIXME:          if del_timestamps:
#FIXME:              cleaned_data["delete_timestamps"] = del_timestamps
#FIXME:          if timestamps:
#FIXME:              cleaned_data["timestamps"] = timestamps
#FIXME:          if assignments:
#FIXME:              cleaned_data["assignments"] = assignments
#FIXME:          return cleaned_data
#FIXME:  
#FIXME:  
#FIXME:  #DEPRECATE
#FIXME:  #class FormAssignmentHandle(forms.Form):
#FIXME:  #    change_log = forms.CharField(widget = forms.HiddenInput(), required = True)
#FIXME:  #
#FIXME:  #    @staticmethod
#FIXME:  #    def _auth(course, userid):
#FIXME:  #        return len(UserCourseBinding.objects.filter(course = course, user__id = userid, is_teacher = True)) == 1
#FIXME:  #
#FIXME:  #    @staticmethod
#FIXME:  #    def _helper_handout(userid, seq):
#FIXME:  #        A = lambda aid: Assignment.objects.get(id = aid)
#FIXME:  #        S = lambda c, gid: { 'n' if g is None else str(g.id): s for g, s in c.groups.items() }[gid]
#FIXME:  #        many = []
#FIXME:  #        for code in seq:
#FIXME:  #            assignment_id, group_id = code.split('-', 1)
#FIXME:  #            assignment = A(assignment_id)
#FIXME:  #            FormAssignmentHandle._auth(assignment.course, userid)
#FIXME:  #            for student in S(assignment.course, group_id):
#FIXME:  #                created = False
#FIXME:  #                try:
#FIXME:  #                    x = UserAssignmentBinding.objects.get(user = student, assignment = assignment)
#FIXME:  #                except UserAssignmentBinding.DoesNotExist:
#FIXME:  #                    x = UserAssignmentBinding(user = student, assignment = assignment)
#FIXME:  #                    created = True
#FIXME:  #                many.append((created, x))
#FIXME:  #        return many
#FIXME:  #
#FIXME:  #    @staticmethod
#FIXME:  #    def _helper_many(userid, seq, state):
#FIXME:  #        A = lambda aid: Assignment.objects.get(id = aid)
#FIXME:  #        S = lambda c, gid: { 'n' if g is None else str(g.id): s for g, s in c.groups.items() }[gid]
#FIXME:  #        many = []
#FIXME:  #        for code in seq:
#FIXME:  #            assignment_id, group_id = code.split('-', 1)
#FIXME:  #            assignment = A(assignment_id)
#FIXME:  #            FormAssignmentHandle._auth(assignment.course, userid)
#FIXME:  #            for student in S(assignment.course, group_id):
#FIXME:  #                x = UserAssignmentBinding.objects.get(user = student, assignment = assignment, state = state)
#FIXME:  #                many.append(x)
#FIXME:  #        return many
#FIXME:  #
#FIXME:  #    def clean(self):
#FIXME:  #        cleaned_data = super().clean()
#FIXME:  #        #raise Exception(str(cleaned_data))
#FIXME:  #        details = json.loads(cleaned_data.pop("change_log"))
#FIXME:  #        userid = details['user_id']
#FIXME:  #        cleaned_data['handout'] = self._helper_handout(userid, details['handoutmany_ids'])
#FIXME:  #        cleaned_data['collect'] = self._helper_many(userid, details['collectmany_ids'], UserAssignmentBinding.ST_WORKINPROGRESS)
#FIXME:  #        cleaned_data['reassign'] = self._helper_many(userid, details['reassignmany_ids'], UserAssignmentBinding.ST_READY)
#FIXME:  #
#FIXME:  #        # authorize
#FIXME:  #        A = lambda uab: self._auth(uab.assignment.course, userid)
#FIXME:  #        cleaned_data['handout'].extend([ (False, uab) for uab in filter(A, UserAssignmentBinding.objects.filter(id__in = details['handout_ids'])) ])
#FIXME:  #        cleaned_data['collect'].extend(filter(A, UserAssignmentBinding.objects.filter(id__in = details['collect_ids'], state = UserAssignmentBinding.ST_WORKINPROGRESS)))
#FIXME:  #        cleaned_data['reassign'].extend(filter(A, UserAssignmentBinding.objects.filter(id__in = details['reassign_ids'], state = UserAssignmentBinding.ST_READY)))
#FIXME:  #        fin_map = {}
#FIXME:  #        for uab in filter(A, UserAssignmentBinding.objects.filter(id__in = details['finalize_ids'], state__in = [UserAssignmentBinding.ST_SUBMITTED, UserAssignmentBinding.ST_COLLECTED, UserAssignmentBinding.ST_READY])):
#FIXME:  #            uab.state = UserAssignmentBinding.ST_READY
#FIXME:  #            fin_map[uab.id] = uab
#FIXME:  #        cleaned_data['finalize'] = list(fin_map.values())
#FIXME:  #
#FIXME:  #        A = lambda aid: Assignment.objects.get(id = aid)
#FIXME:  #        for code in details['create_handout_ids']:
#FIXME:  #            assignment_id, student_id = code.split('-', 1)
#FIXME:  #            assignment = A(assignment_id)
#FIXME:  #            self._auth(assignment.course, userid)
#FIXME:  #            UserCourseBinding.objects.get(course = assignment.course, user__id = student_id, is_teacher = False)
#FIXME:  #            cleaned_data['handout'].append((True, UserAssignmentBinding(user = User.objects.get(id = student_id), assignment = assignment)))
#FIXME:  #
#FIXME:  #        #FIXME: validation error on typerror
#FIXME:  #        rep = lambda d: (int(d['userassignmentbinding_id']), (float(d['score']), d['feedback']))
#FIXME:  #        for k, (score, feedback) in map(rep, details['meta']):
#FIXME:  #            uab = fin_map.get(k, None)
#FIXME:  #            if uab is None:
#FIXME:  #                uab = UserAssignmentBinding.objects.get(id=k)
#FIXME:  #                self._auth(uab.assignment.course, userid)
#FIXME:  #                cleaned_data['finalize'].append(uab)
#FIXME:  #            uab.score = score
#FIXME:  #            uab.feedback_text = feedback
#FIXME:  #
#FIXME:  #        return cleaned_data
#FIXME:  #
#FIXME:  #    def __init__(self, *args, **kwargs):
#FIXME:  #        def A(x):
#FIXME:  #            r = 'qed'
#FIXME:  #            for i in x:
#FIXME:  #                if i != 'dummy':
#FIXME:  #                    r = i
#FIXME:  #            return r
#FIXME:  #        from . import TableAssignmentMass
#FIXME:  ##FIXME: save some here to help authorize later
#FIXME:  #        user = kwargs['initial'].get('user')
#FIXME:  #        super().__init__(*args, **kwargs)
#FIXME:  #        courses = [ b.course for b in UserCourseBinding.objects.filter(user = user, is_teacher = True) ]
#FIXME:  #        assignments = Assignment.objects.filter(course__in = courses)
#FIXME:  #        df_assignment = read_frame(assignments, verbose = False)[['id', 'course']].rename(columns = {'id': 'assignment_id'})
#FIXME:  #        df_ucbs = read_frame(UserCourseBinding.objects.filter(course__in = courses, is_teacher = False), verbose = False)[['id', 'user', 'course']].rename(columns = {'id': 'ucb_id'})
#FIXME:  #        DF_ = pandas.merge(left=df_assignment, right=df_ucbs, left_on='course', right_on='course')[['user', 'assignment_id']].rename(columns={'assignment_id':'assignment'})
#FIXME:  #        DF_['state'] = 'dummy'
#FIXME:  #        df_uabs = read_frame(UserAssignmentBinding.objects.filter(assignment__course__in = courses), verbose = False)[['user', 'assignment', 'state']]
#FIXME:  #        DF_ = pandas.concat([DF_, df_uabs]).groupby(by = ['user', 'assignment']).agg(A).reset_index()
#FIXME:  #        DF = pandas.merge(left = DF_, right = df_assignment, left_on = 'assignment', right_on = 'assignment_id', how = 'inner')
#FIXME:  #        DF = pandas.merge(left = DF, right = df_ucbs, left_on = ['user', 'course'], right_on = ['user', 'course'], how = 'left')
#FIXME:  #        df_ucgbs = read_frame(UserCourseGroupBinding.objects.filter(usercoursebinding__course__in = courses), verbose = False)[['usercoursebinding', 'group']]
#FIXME:  #        DF = pandas.merge(left = DF, right = df_ucgbs, left_on = 'ucb_id', right_on = 'usercoursebinding', how = 'left')[['assignment_id', 'group', 'state', 'user']].fillna(-1)
#FIXME:  #        count = DF.astype({'group': int}).groupby(by = ['assignment_id', 'group', 'state']).agg('count')['user'].to_dict()
#FIXME:  #        groups = CourseGroup.objects.filter(course__in = courses)
#FIXME:  #        if count:
#FIXME:  #            self.okay = True
#FIXME:  #            self.t_mass = TableAssignmentMass( assignments, groups, count )
#FIXME:  #        else:
#FIXME:  #            self.okay = False
#FIXME:  
#FIXME:  
#FIXME:  class FormAssignmentList(forms.Form):
#FIXME:      submit = forms.CharField(widget = forms.HiddenInput(), required = True)
#FIXME:      def clean(self):
#FIXME:          cleaned_data = super().clean()
#FIXME:          details = json.loads(cleaned_data.pop("submit"))
#FIXME:          userid = details['user_id']
#FIXME:          submit_ids = details['submit_ids']
#FIXME:          cleaned_data['submit'] = UserAssignmentBinding.objects.filter(user__id = userid, id__in = submit_ids, state = UserAssignmentBinding.ST_WORKINPROGRESS)
#FIXME:          return cleaned_data
#FIXME:  
#FIXME:  
#FIXME:      def __init__(self, *args, **kwargs):
#FIXME:          from . import TableAssignment
#FIXME:          user = kwargs['initial'].get('user')
#FIXME:          super().__init__(*args, **kwargs)
#FIXME:          courses = [ ucb.course for ucb in UserCourseBinding.objects.filter(user = user, is_teacher = False) ]
#FIXME:          bindings = UserAssignmentBinding.objects.filter(user = user, assignment__course__in = courses)
#FIXME:          if bindings:
#FIXME:              self.okay = True
#FIXME:              self.t_assignment = TableAssignment(bindings)
#FIXME:          else:
#FIXME:              self.okay = False
#FIXME:  
