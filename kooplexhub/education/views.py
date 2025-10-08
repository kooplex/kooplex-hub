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

from hub.tables import TableUsers

from kooplexhub.lib import now

from volume.tables import TableVolume
from hub.templatetags.extras import render_user
from container.models import Image
from education.models import UserCourseBinding
from education.forms import FormCourse
from education.forms import FormAssignment, FormAssignmentList, FormAssignmentConfigure#, FormAssignmentHandle

from .conf import EDUCATION_SETTINGS
from container.conf import CONTAINER_SETTINGS
from canvas.conf import CANVAS_SETTINGS

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
    template_name = 'education/course/list_student.html'
    context_object_name = 'coursebindinglist'

    def get_queryset(self):
        user = self.request.user
        return UserCourseBinding.objects.filter(user = user, is_teacher=False)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['wss_container_control'] = CONTAINER_SETTINGS['wss']['control'].format(user = self.request.user)
        context['wss_course_container'] = EDUCATION_SETTINGS['wss']['containers'].format(user = self.request.user)
        context['wss_handin'] = EDUCATION_SETTINGS['wss']['handin'].format(user = self.request.user)
        return context


class TeacherCourseBindingListView(LoginRequiredMixin, generic.ListView):
    template_name = 'education/course/list_teacher.html'
    context_object_name = 'coursebindinglist'

    def get_queryset(self):
        user = self.request.user
        return UserCourseBinding.objects.filter(user = user, is_teacher=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['wss_container_control'] = CONTAINER_SETTINGS['wss']['control'].format(user = self.request.user)
        context['wss_course_container'] = EDUCATION_SETTINGS['wss']['containers'].format(user = self.request.user)
        context['wss_course_config'] = EDUCATION_SETTINGS['wss']['config'].format(user = self.request.user)
        context['wss_course_users'] = EDUCATION_SETTINGS['wss']['users'].format(user = self.request.user)
        context['wss_assignment_config'] = EDUCATION_SETTINGS['wss']['assignments'].format(user = self.request.user)
        context['wss_assignment_score'] = EDUCATION_SETTINGS['wss']['score'].format(user = self.request.user)
        context['wss_canvas'] = CANVAS_SETTINGS['wss']['courses'].format(user = self.request.user)
        context['wss_canvascourseassignments'] = CANVAS_SETTINGS['wss']['assignments'].format(user = self.request.user)
        context['images'] = Image.objects.filter(imagetype = Image.TP_PROJECT, present = True)
        context['t_volume'] = TableVolume.for_user(self.request.user)
        context['users'] = [ u.profile._repr for u in User.objects.all().exclude(id = self.request.user.id) ]
        context['t_users'] = TableUsers(User.objects.all().exclude(id = self.request.user.id), marker_column='Teacher')
        context['modal_new'] = 'widgets/fetch_canvascourses_modal.html' #FIXME 'education/templates/course/new.html')
        return context


