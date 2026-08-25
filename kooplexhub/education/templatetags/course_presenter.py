from django import template

from education.services.course_presenter import CoursePresenter


register = template.Library()


@register.simple_tag
def present_course(binding):
    return CoursePresenter(
        binding=binding,
    )
