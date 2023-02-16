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

from django_celery_beat.models import ClockedSchedule, PeriodicTask

from kooplexhub.lib import now

from hub.templatetags.extras import render_user
from container.models import Image, Container
from education.models import UserCourseBinding, UserAssignmentBinding, Assignment, CourseContainerBinding, Course
from education.forms import FormCourse
from education.forms import FormAssignment, FormAssignmentList, FormAssignmentConfigure, FormAssignmentHandle
from education.forms import TableAssignment, TableCourseStudentSummary #FIXME: these items shan't show up here

from kooplexhub.settings import KOOPLEX

logger = logging.getLogger(__name__)


@require_http_methods(['GET'])
@login_required
def assignment_teacher(request):
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


@require_http_methods(['GET'])
@login_required
def addcontainer(request, usercoursebinding_id):
    """
    @summary: automagically create an environment
    @param usercoursebinding_id
    """
    from kooplexhub.lib.libbase import standardize_str
    user = request.user
    logger.debug("user %s, method: %s" % (user, request.method))
    try:
        course = UserCourseBinding.objects.get(id = usercoursebinding_id, user = user).course
        container, created = Container.objects.get_or_create(
            name = f'generated for {course.name}', 
            label = f'edu-{user.username}-{standardize_str(course.name)}',
            user = user,
            image = course.image
        )
        CourseContainerBinding.objects.create(course = course, container = container)
        if created:
            messages.info(request, f'We created a new environment {container.name} for course {course.name}.')
        else:
            messages.info(request, f'We associated your course {course.name} with your former environment {container.name}.')
    except Exception as e:
        messages.error(request, f'We failed -- {e}')
        raise
    return redirect('container:list')


class CourseBindingListView(LoginRequiredMixin, generic.ListView):
    template_name = 'course_list.html'
    context_object_name = 'coursebindinglist'

    def get_queryset(self):
        user = self.request.user
        profile = user.profile
        return UserCourseBinding.objects.filter(user = user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['menu_education'] = True
        context['submenu'] = 'courses'
        context['wss_container'] = KOOPLEX.get('hub', {}).get('wss_container', 'wss://localhost/hub/ws/container_environment/{userid}/').format(userid = self.request.user.id)
        return context


class StudentAssignmentListView(LoginRequiredMixin, generic.FormView):
    template_name = 'assignment_student.html'
    form_class = FormAssignmentList
    success_url = '/hub/education/assignment/'

    def get_initial(self):
        initial = super().get_initial()
        user = self.request.user
        initial['user'] = user
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['menu_education'] = True
        context['submenu'] = 'assignment_student'
        context['wss_container'] = KOOPLEX.get('hub', {}).get('wss_container', 'wss://localhost/hub/ws/container_environment/{userid}/').format(userid = self.request.user.id)
        return context

    def form_valid(self, form):
        logger.info(form.cleaned_data)
        for uab in form.cleaned_data['submit']:
            uab.collect(submit = True)
            #FIXME: feedback messages
        return super().form_valid(form)


class ConfigureCourseView(LoginRequiredMixin, generic.edit.UpdateView):
    model = Course
    template_name = 'course_configure.html'
    form_class = FormCourse
    success_url = '/hub/education/course/' #FIXME: django.urls.reverse or shortcuts.reverse does not work reverse('education:courses')

    def get_initial(self):
        initial = super().get_initial()
        user = self.request.user
        initial['user'] = user
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course_id = self.kwargs.get('pk')
        context['menu_education'] = True
        context['submenu'] = 'configure' if course_id else 'new' 
        context['active'] = self.request.COOKIES.get('configure_course_tab', 'meta') if course_id else 'meta'
        context['url_post'] = reverse('education:configure', args = (course_id, )) #TODO: if course_id else reverse('education:new')
        context['course_id'] = course_id
        return context

    def form_valid(self, form):
        logger.info(form.cleaned_data)
        msgs = []
        for group in form.cleaned_data.pop('new_groups', []):
            group.save()
            msgs.append(f"New group {group.name} is created.")
        for group in form.cleaned_data.pop('groups', []):
            group.save()
            msgs.append(f"Updated group {group.name}.")
        del_students = form.cleaned_data.pop('delete_students', None)
        if del_students:
            del_students.delete()
            msgs.append(f"Deleted {len(del_students)} students.")
        del_teachers = form.cleaned_data.pop('delete_teachers', None)
        if del_teachers:
            del_teachers.delete()
            msgs.append(f"Deleted {len(del_teachers)} teachers.")
        for b in form.cleaned_data.pop('new_bindings', []):
            b.save()
            msgs.append("New {} {} added to course".format("teacher" if b.is_teacher else "student", b.user))
        for b in form.cleaned_data.pop('group_bindings_del', []):
            b.delete()
        for b in form.cleaned_data.pop('group_bindings_add', []):
            b.save()
            msgs.append("{b.usercoursebinding.user} is put in group {b.group.name}")
        if msgs:
            logger.info(' '.join(msgs))
            messages.info(self.request, ' '.join(msgs))
        return super().form_valid(form)


class NewAssignmentView(LoginRequiredMixin, generic.FormView):
    model = Assignment
    template_name = 'assignment_new.html'
    form_class = FormAssignment
    success_url = '/hub/education/course/'

    def get_initial(self):
        initial = super().get_initial()
        user = self.request.user
        initial['user'] = user
        return initial

    def get_context_data(self, **kwargs):
        l = reverse('education:courses')
        context = super().get_context_data(**kwargs)
        context['menu_education'] = True
        context['submenu'] = 'assignment_teacher'
        context['active'] = self.request.COOKIES.get('assignment_teacher_tab', 'new')
        return context

    def form_valid(self, form):
        logger.info(form.cleaned_data)
        #authorize
        UserCourseBinding.objects.get(user = self.request.user, course = form.cleaned_data["course"], is_teacher = True)
        msg = f'Assignment {form.cleaned_data["name"]} created in course {form.cleaned_data["course"].name} by {self.request.user}'
        for task in ['task_snapshot', 'task_handout', 'task_collect']:
            if task in form.cleaned_data:
                form.cleaned_data[task].save()
        Assignment.objects.create(**form.cleaned_data)
        logger.info(msg)
        messages.info(self.request, msg)
        return super().form_valid(form)


class ConfigureAssignmentView(LoginRequiredMixin, generic.FormView):
    template_name = 'assignment_configure.html'
    form_class = FormAssignmentConfigure
    success_url = '/hub/education/assignment_handler/'

    def get_initial(self):
        initial = super().get_initial()
        user = self.request.user
        initial['user'] = user
        courses = [ b.course for b in UserCourseBinding.objects.filter(user = user, is_teacher = True) ]
        initial['assignments'] = Assignment.objects.filter(course__in = courses)
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['menu_education'] = True
        context['submenu'] = 'assignment_teacher'
        context['active'] = self.request.COOKIES.get('assignment_teacher_tab', 'conf')
        return context

    def form_valid(self, form):
        logger.info(form.cleaned_data)
        msgs = []
        for ts in form.cleaned_data.get("timestamps", []):
            ts.save()
        for tsk in form.cleaned_data.get("tasks", []):
            tsk.save()
        for ts in form.cleaned_data.get("delete_timestamps", []):
            ts.delete()
        for a in form.cleaned_data.get("delete_assignments", []):
            a.delete()
            msgs.append(f"Assignment {a.name} is deleted from course {a.course.name}.")
        for a in form.cleaned_data.get("assignments", []):
            a.save()
            msgs.append(f"Assignment {a.name} in course {a.course.name} is updated.")
        if msgs:
            logger.info(' '.join(msgs))
            messages.info(self.request, ' '.join(msgs))
        return super().form_valid(form)


class HandleAssignmentView(LoginRequiredMixin, generic.FormView):
    template_name = 'assignment_handle.html'
    form_class = FormAssignmentHandle
    success_url = '/hub/education/assignment_handler/'

    def get_initial(self):
        initial = super().get_initial()
        user = self.request.user
        initial['user'] = user
        return initial

    def get_context_data(self, **kwargs):
        user = self.request.user
        context = super().get_context_data(**kwargs)
        context['menu_education'] = True
        context['submenu'] = 'assignment_teacher'
        context['active'] = self.request.COOKIES.get('assignment_teacher_tab', 'handle')
        return context

#FIXME
    def form_valid(self, form):
        logger.info(form.cleaned_data)
        raise Exception(str(form.cleaned_data))
#        msgs = []
#        for a in form.cleaned_data.get("delete_assignments", []):
#            a.delete()
#            msgs.append(f"Assignment {a.name} is deleted from course {a.course.name}.")
#        for a in form.cleaned_data.get("assignments", []):
#            a.save()
#            msgs.append(f"Assignment {a.name} in course {a.course.name} is updated.")
#        if msgs:
#            logger.info(' '.join(msgs))
#            messages.info(self.request, ' '.join(msgs))
        return super().form_valid(form)





#FIXME: refactor me
@require_http_methods(['GET'])
@login_required
def assignment_summary(request):
    user = request.user
    courses = [ b.course for b in UserCourseBinding.objects.filter(user = user, is_teacher = True) ]
    assignments = list(Assignment.objects.filter(course__in = courses))
    context_dict = {
        'menu_education': True,
        'submenu': 'assignment_teacher',
        'active': request.COOKIES.get('assignment_teacher_tab', 'summary'),
        'd_course_assignments': { c:l for c, l in { c: list(filter(lambda a: a.course == c, assignments)) for c in courses }.items() if l },
        't_summary': dict(filter(lambda i: i[1] is not None, { c.id: TableCourseStudentSummary(c) for c in courses }.items())),
    }
    return render(request, 'assignment.html', context = context_dict)


