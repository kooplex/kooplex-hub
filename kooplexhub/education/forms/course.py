from django import forms
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html

from container.models import Image
from education.models import Course

from kooplexhub.common import tooltip_attrs
from kooplexhub.lib import my_slug_validator, my_end_validator


class FormCourse(forms.ModelForm):
    class Meta:
        model = Course
        fields = [ 'name', 'description', 'image' ]

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
        required = False, empty_label = 'Select image...',
        widget = forms.Select(attrs = tooltip_attrs({ 'title': _('Select an image you recommend your students the most to work with during the semester in the given course.') })),
    )

    def descriptions(self):
        hidden = lambda i: f"""
<input type="hidden" id="image-description-{i.id}" value="{i.description}">
<input type="hidden" id="image-thumbnail-{i.id}" value="{i.thumbnail.img_src}">
        """
        return format_html("".join(list(map(hidden, self.fields['image'].queryset))))

    def __init__(self, *args, **kwargs):
        from ..forms import TableUser
        user = kwargs['initial'].get('user')
        super().__init__(*args, **kwargs)
        course = kwargs.get('instance', Course())
        self.t_teachers_add = TableUser(course, user, teacher_selector = True, bind_table = False)
        self.t_teachers = TableUser(course, user, teacher_selector = True, bind_table = True)
        self.t_students_add = TableUser(course, user, teacher_selector = False, bind_table = False)
        self.t_students = TableUser(course, user, teacher_selector = False, bind_table = True)
#            't_group': TableGroup(CourseGroup.objects.filter(course = course)),


