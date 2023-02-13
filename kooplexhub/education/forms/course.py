import json
from django import forms
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html

from django.contrib.auth.models import User
from container.models import Image
from education.models import Course, CourseGroup, UserCourseBinding, UserCourseGroupBinding

from kooplexhub.common import tooltip_attrs
from kooplexhub.lib import my_slug_validator, my_end_validator


class FormCourse(forms.ModelForm):
    class Meta:
        model = Course
        fields = [ 'name', 'description', 'image' ]

    course_config = forms.CharField(widget = forms.HiddenInput(), required = False)
    name = forms.CharField(
        label = _("Course name"),
        max_length = 100, required = True,
        widget = forms.TextInput(attrs = tooltip_attrs({ 'title': _('A short name of the course, but it has to be unique among course names.') })),
    )
    description = forms.CharField(
        max_length = 100, required = True,
        widget = forms.Textarea(attrs = tooltip_attrs({
            'rows': 3, 
            'title': _('It is always a good idea to have a description of your course.'), 
        })),
    )
    image = forms.ModelChoiceField(
        label = _('Preferred image'),
        queryset = Image.objects.filter(imagetype = Image.TP_PROJECT, present = True), 
        required = True, empty_label = 'Select image...',
        widget = forms.Select(attrs = tooltip_attrs({ 'title': _('Select an image you recommend your students the most to work with during the semester in the given course.') })),
    )

    def descriptions(self):
        hidden = lambda i: f"""
<input type="hidden" id="image-description-{i.id}" value="{i.description}">
<input type="hidden" id="image-thumbnail-{i.id}" value="{i.thumbnail.img_src}">
        """
        return format_html("".join(list(map(hidden, self.fields['image'].queryset))))

    def __init__(self, *args, **kwargs):
        from . import TableUser, TableGroup
        user = kwargs['initial'].get('user')
        super().__init__(*args, **kwargs)
        course = kwargs.get('instance', Course())
        self.t_teachers_add = TableUser(course, user, teacher_selector = True, bind_table = False)
        self.t_teachers = TableUser(course, user, teacher_selector = True, bind_table = True)
        self.t_students_add = TableUser(course, user, teacher_selector = False, bind_table = False)
        self.t_students = TableUser(course, user, teacher_selector = False, bind_table = True)
        groups = list(CourseGroup.objects.filter(course = course))
        groups.append(CourseGroup())
        self.t_group = TableGroup(groups)

    def clean(self):
        cleaned_data = super().clean()
        extra = json.loads(cleaned_data.pop('course_config'))
        courseid = extra.get('course_id')
        userid = extra.get('user_id')
        user = User.objects.get(id = userid)
        coursename = cleaned_data.get('name')
        coursedescription = cleaned_data.get('description')
        ve = []
        if not coursename:
            ve.append( forms.ValidationError(_(f'Course name cannot be empty'), code = 'invalid name') )
        if not coursedescription:
            ve.append( forms.ValidationError(_(f'Course description cannot be empty'), code = 'invalid description') )
        # authorize
        course = Course.objects.get(id = courseid)
        UserCourseBinding.objects.get(user = user, course = course, is_teacher = True)
        # manage users
        teachers = set(map(lambda i: int(i), extra.pop('teachers', [])))
        teachers_before = { b.user.id for b in UserCourseBinding.objects.filter(course = course, is_teacher = True) }
        students = set(map(lambda i: int(i), extra.pop('students', [])))
        students_before = { b.user.id for b in UserCourseBinding.objects.filter(course = course, is_teacher = False) }
        skip_grouping = False
        if teachers.intersection(students):
            ve.append( forms.ValidationError(_(f'A user cannot be a teacher or a student at the same time'), code = 'duplicate') )
        if students_before.difference(students):
            cleaned_data['delete_students'] = UserCourseBinding.objects.filter(course = course, user__id__in = students_before.difference(students))
            skip_grouping = True
        if teachers_before.difference(teachers):
            cleaned_data['delete_teachers'] = UserCourseBinding.objects.filter(course = course, user__id__in = teachers_before.difference(teachers))
        new_users = []
        for uid in students.difference(students_before):
            u = User.objects.get(id = uid)
            new_users.append(UserCourseBinding(user = u, course = course, is_teacher = False))
            skip_grouping = True
        for uid in teachers.difference(teachers_before):
            u = User.objects.get(id = uid)
            new_users.append(UserCourseBinding(user = u, course = course, is_teacher = True))
        if new_users:
            cleaned_data['new_bindings'] = new_users
        # manage groups
        new_groups = []
        for name, description in extra.pop('new_group'):
            if name and description:
                new_groups.append( CourseGroup(name = name, description = description, course = course) )
            else:
                ve.append( forms.ValidationError(_(f'Group name and/or description cannot be empty'), code = 'invalid name') )
        if new_groups:
            cleaned_data['new_groups'] = new_groups
        update_groups = []
        for gid, name, description in extra.pop('group'):
            if name and description:
                group = CourseGroup.objects.get(course = course, id = gid)
                group.name = name
                group.description = description
                update_groups.append(group)
            else:
                ve.append( forms.ValidationError(_(f'Group name and/or description cannot be empty'), code = 'invalid name') )
        if update_groups:
            cleaned_data['groups'] = update_groups
        # manage grouping
        group_bindings_add = []
        group_bindings_del = []
        if not skip_grouping:
            for gid, students in extra.pop('grouping'):
                if gid == 'n':
                    continue
                group = CourseGroup.objects.get(id = gid, course = course)
                students_old = { b.usercoursebinding.user.id for b in UserCourseGroupBinding.objects.filter(group = group) }
                group_bindings_del.extend( UserCourseGroupBinding.objects.filter(
                    usercoursebinding__user__id__in = set(students_old).difference(students),
                    group = group, usercoursebinding__course = course,
                    usercoursebinding__is_teacher = False
                ))
                for uid in set(students).difference(students_old):
                    u = User.objects.get(id = uid)
                    b = UserCourseBinding.objects.get(user = u, course = course, is_teacher = False)
                    group_bindings_add.append(UserCourseGroupBinding(group = group, usercoursebinding = b))
        if group_bindings_del:
            cleaned_data['group_bindings_del'] = group_bindings_del
        if group_bindings_add:
            cleaned_data['group_bindings_add'] = group_bindings_add
        if ve:
            raise forms.ValidationError(ve)
        return cleaned_data

