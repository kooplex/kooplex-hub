from django import template

from education.services.course_presenter import CoursePresenter


register = template.Library()


@register.simple_tag(takes_context=True)
def present_course(context, binding):
    return CoursePresenter(
        binding=binding,
        user=context["request"].user,
    )
