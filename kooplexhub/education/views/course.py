import logging
import datetime

from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.views import generic
from django.views.generic.edit import FormView
from django.template.response import TemplateResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.core.exceptions import PermissionDenied

from kooplexhub.lib.libbase import standardize_str
from ..models import UserCourseBinding
from ..forms import CourseCreateForm
from ..services.course_presenter import CoursePresenter


logger = logging.getLogger(__name__)


#FIXME
@login_required
def delete_or_leave(request, pk_course, pk_user):
    """Delete or leave a course."""
    user = request.user
    teachers=UserCourseBinding.objects.filter(course_id=pk_course, is_teacher=True)
    if not teachers:
        return redirect('education:teaching')
    caller=teachers.filter(user_id=pk_user).first()
    others=teachers.exclude(user_id=pk_user)
    if caller:
        if others:
            logger.debug(f'leave course {caller}')
            logger.debug(others)
            caller.delete()
        else:
            logger.debug(f'delete course by {caller}')
            caller.course.delete()
    return redirect('education:teaching')


class CourseLeaveView(
    LoginRequiredMixin, 
    generic.View,
):

    def post(self, request, course_id, *args, **kwargs):
        binding = get_object_or_404(
            UserCourseBinding,
            user=request.user,
            course_id=course_id,
        )
        #FIXME


#TODO: place in mixins.py
class CourseBindingMixin:
    def get_course_binding_queryset(self):
        return (
            UserCourseBinding.objects
            .for_user(self.request.user)
            .with_course()
        )


class CourseListQuerysetMixin(CourseBindingMixin):
    context_object_name = "coursebindings"

    def get_queryset(self):
        return (
            self.get_course_binding_queryset()
            .ordered_for_dashboard()
        )



class CourseListView(
    LoginRequiredMixin, 
    CourseListQuerysetMixin,
    generic.ListView,
):
    template_name = "education/course/list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["courses"] = [
            CoursePresenter(
                binding=binding,
                user=self.request.user,
            )
            for binding in context["coursebindings"]
        ]

        return context


class CourseGridView(
    LoginRequiredMixin,
    CourseListQuerysetMixin,
    generic.ListView,
):
    template_name = "education/course/partials/grid.html"


class CourseCardView(
    LoginRequiredMixin,
    CourseBindingMixin,
    generic.TemplateView,
):
    template_name = (
        "education/course/partials/card_wrapper.html"
    )

    def get_binding(self):
        return get_object_or_404(
            self.get_course_binding_queryset(),
            course_id=self.kwargs["course_id"],
        )


