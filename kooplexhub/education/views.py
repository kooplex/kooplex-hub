import logging
import re
import json
import datetime

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views import generic
from django.views.decorators.http import require_http_methods
from django.utils.html import format_html
from django.urls import reverse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.db import IntegrityError

from hub.forms import TableUsers

from kooplexhub.lib import now

from container.forms import TableVolume
from hub.templatetags.extras import render_user
from container.models import Image, Container
from education.models import UserCourseBinding, UserAssignmentBinding, Assignment, CourseContainerBinding, Course
from education.forms import FormCourse
from education.forms import FormAssignment, FormAssignmentList, FormAssignmentConfigure#, FormAssignmentHandle

from kooplexhub.settings import KOOPLEX

logger = logging.getLogger(__name__)


@login_required
def delete_or_leave(request, pk_course, pk_user):
    """Delete or leave a course."""
    from canvas.models import CanvasCourse
    #FIXME: decouple canvas as trigger?
    user = request.user
    canvascourse=CanvasCourse.objects.filter(course_id=pk_course).first()
    if canvascourse:
        canvascourse.delete()
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


@require_http_methods(['GET'])
@login_required
def assignment_teacher(request):
    """
    @summary: handle the tabs in the teacher's assignment page
    """
    active = request.COOKIES.get('assignment_teacher_tab', 'conf')
    if active == 'new':
        return redirect('education:assignment_new')
    elif active == 'conf':
        return redirect('education:assignment_configure')
    elif active == 'handle':
        return redirect('education:assignment_handle')
    elif active == 'summary':
        return redirect('education:assignment_summary')
    else:
        logger.error(f'not implemented tab: {active} by {request.user}')
        return redirect('indexpage')


class StudentCourseBindingListView(LoginRequiredMixin, generic.ListView):
    template_name = 'course_list.html'
    context_object_name = 'coursebindinglist'

    def get_queryset(self):
        user = self.request.user
        return UserCourseBinding.objects.filter(user = user, is_teacher=False)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['wss_container'] = KOOPLEX.get('hub', {}).get('wss_container_control', 'wss://localhost/hub/ws/container_environment/{userid}/').format(userid = self.request.user.id)
        context['wss_course_container'] = KOOPLEX.get('hub', {}).get('wss_course_container', 'wss://localhost/hub/ws/education/container/{userid}/').format(userid = self.request.user.id)
        context['wss_handin'] = KOOPLEX.get('hub', {}).get('wss_course_handin', 'wss://localhost/hub/ws/education/handin/{userid}/').format(userid = self.request.user.id)
        context['search_placeholder'] = 'Search course...'
        context['search_what'] = 'course'
        return context


class TeacherCourseBindingListView(LoginRequiredMixin, generic.ListView):
    template_name = 'course_admin.html'
    context_object_name = 'coursebindinglist'

    def get_queryset(self):
        user = self.request.user
        return UserCourseBinding.objects.filter(user = user, is_teacher=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['wss_container'] = KOOPLEX.get('hub', {}).get('wss_container_control', 'wss://localhost/hub/ws/container_environment/{userid}/').format(userid = self.request.user.id)
        context['wss_course_container'] = KOOPLEX.get('hub', {}).get('wss_course_container', 'wss://localhost/hub/ws/education/container/{userid}/').format(userid = self.request.user.id)
        context['wss_course_config'] = KOOPLEX.get('hub', {}).get('wss_course_config', 'wss://localhost/hub/ws/course/config/{userid}/').format(userid = self.request.user.id)
        context['wss_assignment_config'] = KOOPLEX.get('hub', {}).get('wss_assignment_config', 'wss://localhost/hub/ws/assignment/config/{userid}/').format(userid = self.request.user.id)
        context['wss_canvas'] = KOOPLEX.get('hub', {}).get('wss_canvas', 'wss://localhost/hub/ws/canvas/fetchcourses/{userid}/').format(userid = self.request.user.id)
        context['images'] = Image.objects.filter(imagetype = Image.TP_PROJECT, present = True)
        context['t_volume'] = TableVolume(self.request.user)
        context['users'] = [ u.profile._repr for u in User.objects.all().exclude(id = self.request.user.id) ]
        context['t_users'] = TableUsers(User.objects.all().exclude(id = self.request.user.id), marker_column='Teacher')
        context['empty_course'] = Course()
        context['modal_new'] = KOOPLEX.get('education', {}).get('new_course', 'new_course.html')
        context['search_placeholder'] = 'Search course...'
        context['search_what'] = 'course'
        return context


