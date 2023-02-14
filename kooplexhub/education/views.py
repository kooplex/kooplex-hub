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
from education.forms import FormAssignment, FormAssignmentConfigure
from education.forms import TableAssignment, TableAssignmentConf, TableAssignmentHandle, TableAssignmentMass, TableAssignmentSummary, TableAssignmentMassAll, TableAssignmentStudentSummary, TableCourseStudentSummary

from kooplexhub.settings import KOOPLEX

logger = logging.getLogger(__name__)

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
        context['empty_title'] = "You have not been added to any courses yet as a teacher"
        context['empty_body'] = format_html("""If this is unexpected, please ask system administrator to take care of it. <a href="mailto:kooplex@elte.hu"><i class="bi bi-envelope"></i><span>&nbsp;Send e-mail...</span></a>""")
        context['wss_container'] = KOOPLEX.get('hub', {}).get('wss_container', 'wss://localhost/hub/ws/container_environment/{userid}/').format(userid = self.request.user.id)
        return context


class StudentAssignmentListView(LoginRequiredMixin, generic.TemplateView):
    template_name = 'assignment_student.html'

    def get_context_data(self, **kwargs):
        l = reverse('education:courses')
        context = super().get_context_data(**kwargs)
        context['menu_education'] = True
        context['submenu'] = 'assignment_student'
        context['empty_title'] = "You have not received an assignment yet"
        context['empty_body'] = format_html(f"""<a href="{l}"><i class="bi bi-journal-bookmark-fill"></i><span class="d-none d-sm-inline">&nbsp;list your courses</span></a>""")
        user = self.request.user
        profile = user.profile
        if 'usercoursebinding_id' in self.kwargs:
            courses = [ UserCourseBinding.objects.get(user = user, is_teacher = False, id = self.kwargs['usercoursebinding_id']).course ]
        else:
            courses = [ ucb.course for ucb in UserCourseBinding.objects.filter(user = user, is_teacher = False) ]
        context['t_assignment'] = TableAssignment(UserAssignmentBinding.objects.filter(user = user, assignment__course__in = courses))
        return context


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
        user = self.request.user
        profile = user.profile
        if 'usercoursebinding_id' in self.kwargs:
            courses = [ UserCourseBinding.objects.get(user = user, is_teacher = False, id = self.kwargs['usercoursebinding_id']).course ]
        else:
            courses = [ ucb.course for ucb in UserCourseBinding.objects.filter(user = user, is_teacher = False) ]
        context['t_assignment'] = TableAssignment(UserAssignmentBinding.objects.filter(user = user, assignment__course__in = courses))
        return context

    def form_valid(self, form):
        logger.info(form.cleaned_data)
        #authorize
        UserCourseBinding.objects.get(user = self.request.user, course = form.cleaned_data["course"], is_teacher = True)
        msg = f'Assignment {form.cleaned_data["name"]} created in course {form.cleaned_data["course"].name} by {self.request.user}'
        for task in ['task_snapshot', 'task_handout', 'task_collect']:
            if task in form.cleaned_data:
                form.cleaned_data[task].clocked.save()
                form.cleaned_data[task].save()
        Assignment.objects.create(**form.cleaned_data)
        logger.info(msg)
        messages.info(self.request, msg)
        return super().form_valid(form)


class ConfigureAssignmentView(LoginRequiredMixin, generic.FormView):
    template_name = 'assignment_configure.html'
    form_class = FormAssignmentConfigure
    success_url = '/hub/education/course/'

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
        for a in form.cleaned_data["delete_assignments"]:
            a.delete()
            msgs.append(f"Assignment {a.name} is deleted from course {a.course.name}.")
        for a in form.cleaned_data["assignments"]:
            a.save()
            msgs.append(f"Assignment {a.name} in course {a.course.name} is updated.")
        if msgs:
            messages.info(self.request, ' '.join(msgs))
        return super().form_valid(form)



@require_http_methods(['GET'])
@login_required
def assignment_teacher(request):
    active = request.COOKIES.get('assignment_teacher_tab', 'conf')
    if active == 'new':
        return redirect('education:assignment_new')
    elif active == 'conf':
        return redirect('education:assignment_configure')
    elif active == 'handle':
        return redirect('education:assignment_handler')
    elif active == 'handlemass':
        return redirect('education:assignment_mass')
    elif active == 'summary':
        return redirect('education:assignment_summary')
    else:
        logger.error(f'not implemented tab: {active} by {request.user}')
        return redirect('indexpage')



def _extract_timestamp(d):
    df, hm = d.split(', ')
    M, D, Y = df.split('/')
    h, m = hm.split(':')
    return {'year': int(Y), 'month': int(M), 'day': int(D), 'hour': int(h), 'minute': int(m)}

@require_http_methods(['POST'])
@login_required
def assignment_configure_(request):
    """
    @summary: handle creation of a new assignment
    """
    user = request.user
    logger.debug("user %s, method: %s" % (user, request.method))
    courses = [ ucb.course for ucb in UserCourseBinding.objects.filter(user = user, is_teacher = True) ]
    delete_ids = request.POST.getlist('selection_delete', [])
    d = []
    oops = []
    for aid in delete_ids:
        try:
            a = Assignment.objects.get(id = aid, course__in = courses)
            assert (a.creator == user) or (a.course.teacher_can_delete_foreign_assignment), f"{user} is not the creator of assignment {a.name} in course {a.course.name} and delete foreign is not set"
            ##################################################
            # do not archive user's handout assignment folders
            a.remove_collected = True
            a.save()
            ##################################################
            a.delete()
            logger.info(f'- deleted assignment {a.name} ({a.folder}) from course {a.course.name} by {user.username}')
            d.append(f'{a.name} by {a.creator}')
        except AssertionError:
            oops.append(a.name)
            raise
        except Exception as e:
            logger.error(e)
    if len(d):
        a = ', '.join(d)
        messages.info(request, f'Deleted assignment(s) {a}.')
    if len(oops):
        a = ', '.join(oops)
        messages.warning(request, f'You are not allowed to delete assignment(s) {a}.')
    assignment_ids = set()
    for k in request.POST.keys():
        if k.startswith('name-old-'):
            assignment_ids.add(k.split('-')[-1])
    other_ids = assignment_ids.difference(delete_ids)
    m = []
    tb = {'valid_from': 'task_handout', 'expires_at': 'task_collect'}
    for aid in other_ids:
        a = Assignment.objects.get(id = aid, course__in = courses)
        changed = []
        for attr in [ 'valid_from', 'expires_at' ]:
            old = request.POST.get(f'{attr}-old-{aid}')
            new = request.POST.get(f'{attr}-{aid}')
            if old != new:
                changed.append(f"{attr} from {old} to {new}")
                task = getattr(a, tb[attr])
                if old and not new:
                    task.clocked.delete()
                    setattr(a, tb[attr], None)
                elif not old and new:
                    schedule = ClockedSchedule.objects.create(clocked_time = datetime.datetime(**_extract_timestamp(new)))
                    setattr(a, tb[attr], PeriodicTask.objects.create(
                        name = f"{tb[attr]}_{a.id}",
                        task = "education.tasks.assignment_handout",
                        clocked = schedule,
                        one_off = True,
                        kwargs = json.dumps({
                            'assignment_id': a.id,
                        })
                    ))
                else:
                    task.clocked.clocked_time = datetime.datetime(**_extract_timestamp(new))
                    task.clocked.save()

        for attr in [ 'name', 'description', 'max_size' ]:
            old = request.POST.get(f'{attr}-old-{aid}')
            new = request.POST.get(f'{attr}-{aid}')
            if old != new:
                changed.append(f"{attr} from {old} to {new}")
                setattr(a, attr, new if new else None)
        if len(changed):
            a.save()
            logger.info(f'. modified assignment {a.name} ({a.folder}) from course {a.course.name} by {user.username}')
            cl = ', '.join(changed)
            m.append(f'{a.name}: {cl}')
    if len(m):
        cl = '; '.join(m)
        messages.info(request, f'Configured assignment(s) {cl}.')
    return redirect('education:assignment_teacher')

@require_http_methods(['GET'])
@login_required
def assignment_handler(request):
    user = request.user
    courses = [ b.course for b in UserCourseBinding.objects.filter(user = user, is_teacher = True) ]
    assignments = list(Assignment.objects.filter(course__in = courses))
    uabs = list(UserAssignmentBinding.objects.filter(assignment__in = assignments))
    lut_uabs = { a: list(filter(lambda b: b.assignment == a, uabs)) for a in assignments }
    groups = { c: c.groups for c in courses }
    context_dict = {
        'menu_education': True,
        'submenu': 'assignment_teacher',
        'active': request.COOKIES.get('assignment_teacher_tab', 'handle'),
        'd_course_assignments': { c:l for c, l in { c: list(filter(lambda a: a.course == c, assignments)) for c in courses }.items() if l },
        't_mass': { a.id: TableAssignmentMass( a, lut_uabs[a], groups[a.course] ) for a in assignments },
        't_assignments': { a.id: TableAssignmentHandle( lut_uabs[a] ) for a in assignments },
    }
    return render(request, 'assignment_handle.html', context = context_dict)

@require_http_methods(['POST'])
@login_required
def assignment_individual_handle(request):
    """ TBA """
    user = request.user
    logger.debug(f"HANDLE user {user}, method: {request.method}")
    courses = [ ucb.course for ucb in UserCourseBinding.objects.filter(user = user, is_teacher = True) ]
    oops = []
    msgs = []
    # handout
    n_handout = 0
    n_handout_error = 0
    extr = [ json.loads(x) for x in request.POST.getlist('selection_handout', []) ]
    for aid, uid in extr:
        try:
            a = Assignment.objects.get(id = aid, course__in = courses)
            u = UserCourseBinding.objects.get(user__id = uid, course = a.course, is_teacher = False).user
            UserAssignmentBinding.objects.create(user = u, assignment = a).handout()
            n_handout += 1
        except Exception as e:
            logger.error(e)
            n_handout_error += 1
            oops.append(str(e))
    if n_handout:
        msgs.append(f'Handed {n_handout} assignments out.')
    # collect
    n_collected = 0
    n_collect_error = 0
    for uab_id in request.POST.getlist('selection_collect', []):
        try:
            uab = UserAssignmentBinding.objects.get(id = uab_id, assignment__course__in = courses).handout()
            uab.state = UserAssignmentBinding.ST_COLLECTED
            uab.submitted_at = now()
            uab.save()
            n_collected += 1
        except Exception as e:
            logger.error(e)
            n_collect_error += 1
            oops.append(str(e))
    if n_collected:
        msgs.append(f'Collected {n_collected} assignments.')
    # correct
    n_corrected = 0
    n_correct_error = 0
    for uab_id in request.POST.getlist('selection_correct', []):
        try:
            uab = UserAssignmentBinding.objects.get(id = uab_id, assignment__course__in = courses, state__in = [ UserAssignmentBinding.ST_COLLECTED, UserAssignmentBinding.ST_SUBMITTED ])
            uab.extract2correct()
            n_corrected += 1
        except Exception as e:
            logger.error(e)
            n_correct_error += 1
            oops.append(str(e))
    if n_collected:
        msgs.append(f'Marked {n_corrected} assignments for correction.')
    # feedback
    n_feedback = 0
    n_feedback_error = 0
    for uab_id in request.POST.getlist('selection_finalize', []):
        try:
            uab = UserAssignmentBinding.objects.get(id = uab_id, assignment__course__in = courses, state = UserAssignmentBinding.ST_CORRECTED)
            uab.finalize(user, message = request.POST.get(f'feedback_text-{uab_id}'), score = request.POST.get(f'score-{uab_id}'))
            n_feedback += 1
        except Exception as e:
            logger.error(e)
            n_feedback_error += 1
            oops.append(str(e))
    if n_feedback:
        msgs.append(f'Ready with {n_feedback} assignments.')
    # updated score or feedback_text
    n_updated = 0
    n_update_error = 0
    for uab_id in request.POST.getlist('ready_ids', []):
        score = request.POST.get(f'score-{uab_id}')
        feedback_text = request.POST.get(f'feedback_text-{uab_id}')
        if (request.POST.get(f'score-old-{uab_id}') == score) and (request.POST.get(f'feedback_text-old-{uab_id}') == feedback_text):
            continue
        try:
            uab = UserAssignmentBinding.objects.get(id = uab_id, assignment__course__in = courses, state = UserAssignmentBinding.ST_READY)
            uab.score = score
            uab.feedback_text = feedback_text
            uab.save()
            n_updated += 1
        except Exception as e:
            logger.error(e)
            n_update_error += 1
            oops.append(str(e))
    if n_updated:
        msgs.append(f'{n_updated} assignment scores and or feedback messages were edited and saved.')
    # reassign
    n_reassign = 0
    n_reassign_error = 0
    for uab_id in request.POST.getlist('selection_reassign', []):
        try:
            uab = UserAssignmentBinding.objects.get(id = uab_id, assignment__course__in = courses, state = UserAssignmentBinding.ST_READY)
            uab.reassign()
            n_reassign += 1
        except Exception as e:
            logger.error(e)
            n_reassign_error += 1
            oops.append(str(e))
    if n_reassign:
        msgs.append(f'{n_reassign} assignments were reassigned.')
    if len(msgs):
        messages.info(request,' '.join(msgs))
    if len(oops):
        messages.error(request,' '.join(oops))
    return redirect('education:assignment_teacher')

@require_http_methods(['GET'])
@login_required
def assignment_mass(request):
    user = request.user
    courses = [ b.course for b in UserCourseBinding.objects.filter(user = user, is_teacher = True) ]
    assignments = list(Assignment.objects.filter(course__in = courses))
    uabs = list(UserAssignmentBinding.objects.filter(assignment__in = assignments))
    lut_uabs = { a: list(filter(lambda b: b.assignment == a, uabs)) for a in assignments }
    groups = { c: c.groups for c in courses }
    context_dict = {
        'menu_education': True,
        'submenu': 'assignment_teacher',
        'active': request.COOKIES.get('assignment_teacher_tab', 'handlemass'),
        't_mass_all': TableAssignmentMassAll( assignments, lut_uabs, groups ),
    }
    return render(request, 'assignment_handle_mass.html', context = context_dict)

@require_http_methods(['POST'])
@login_required
def assignment_mass_(request):
    user = request.user
    profile = user.profile
    logger.debug("user %s, method: %s" % (user, request.method))
    ex = lambda x: None if x == 'n' else int(x)
    handout = []
    for idx in request.POST.getlist('handout'):
        a, g = idx.split('-')
        assignment = Assignment.objects.get(id = a)
        groups = dict(map(lambda x: (None if x[0] is None else x[0].id, x[1]), assignment.course.groups.items()))
        handout.extend(_handout(assignment, { ex(g): groups[ex(g)] }))
    if len(handout):
        messages.info(request, 'received: ' + ', '.join(list(map(lambda s: str(s), handout))))
    collect = []
    for idx in request.POST.getlist('collect'):
        a, g = idx.split('-')
        assignment = Assignment.objects.get(id = a)
        groups = dict(map(lambda x: (None if x[0] is None else x[0].id, x[1]), assignment.course.groups.items()))
        collect.extend(_collect(assignment, { ex(g): groups[ex(g)] }))
    if len(collect):
        messages.info(request, 'collected: ' + ', '.join(list(map(lambda s: str(s), collect))))
    correct = []
    for idx in request.POST.getlist('correct'):
        a, g = idx.split('-')
        assignment = Assignment.objects.get(id = a)
        groups = dict(map(lambda x: (None if x[0] is None else x[0].id, x[1]), assignment.course.groups.items()))
        correct.extend(_correct(assignment, { ex(g): groups[ex(g)] }))
    if len(correct):
        messages.info(request, 'corrected: ' + ', '.join(list(map(lambda s: str(s), correct))))
    reassign = []
    for idx in request.POST.getlist('reassign'):
        a, g = idx.split('-')
        assignment = Assignment.objects.get(id = a)
        groups = dict(map(lambda x: (None if x[0] is None else x[0].id, x[1]), assignment.course.groups.items()))
        reassign.extend(_reassign(assignment, { ex(g): groups[ex(g)] }))
    if len(reassign):
        messages.info(request, 'reassigned: ' + ', '.join(list(map(lambda s: str(s), correct))))
    return redirect('education:assignment_teacher')

@login_required
def assignment_mass___(request):
    user = request.user
    profile = user.profile
    logger.debug("user %s, method: %s" % (user, request.method))
    assignment_id = request.POST.get('assignment')
    assignment = Assignment.objects.get(id = assignment_id)
    UserCourseBinding.objects.get(user = user, course = assignment.course, is_teacher = True)
    groups = dict(map(lambda x: (None if x[0] is None else x[0].id, x[1]), assignment.course.groups.items()))
    ex = lambda x: None if x == 'n' else int(x)
    request.COOKIES['assignment_id'] = assignment_id
    handout = _handout(assignment, { x: groups[x] for x in map(ex, request.POST.getlist('handout')) })
    if len(handout):
        messages.info(request, 'received: ' + ', '.join(list(map(lambda s: str(s), handout))))
    collect = _collect(assignment, { x: groups[x] for x in map(ex, request.POST.getlist('collect')) })
    if len(collect):
        messages.info(request, 'collected: ' + ', '.join(list(map(lambda s: str(s), collect))))
    correct = _correct(assignment, { x: groups[x] for x in map(ex, request.POST.getlist('correct')) })
    if len(correct):
        messages.info(request, 'corrected: ' + ', '.join(list(map(lambda s: str(s), correct))))
    reassign = _reassign(assignment, { x: groups[x] for x in map(ex, request.POST.getlist('reassign')) })
    if len(reassign):
        messages.info(request, 'reassigned: ' + ', '.join(list(map(lambda s: str(s), correct))))
    return redirect('education:assignment_teacher')

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


def _handout(assignment, group_map):
    uab = UserAssignmentBinding.objects.filter(assignment = assignment)
    handout = []
    for g, students in group_map.items():
        for s in students:
            try:
                b = uab.get(user = s)
                if b.state != UserAssignmentBinding.ST_QUEUED:
                    continue
                b.handout()
            except UserAssignmentBinding.DoesNotExist:
                UserAssignmentBinding.objects.create(user = s, assignment = assignment, state = UserAssignmentBinding.ST_WORKINPROGRESS).handout()
            handout.append(s)
    return handout

def _collect(assignment, group_map):
    uab = UserAssignmentBinding.objects.filter(assignment = assignment)
    collect = []
    for g, students in group_map.items():
        for b in uab.filter(state = UserAssignmentBinding.ST_WORKINPROGRESS, user__in = students):
            b.collect(False)
            collect.append(b.user)
    return collect

def _correct(assignment, group_map):
    uab = UserAssignmentBinding.objects.filter(assignment = assignment)
    correct = []
    for g, students in group_map.items():
        for b in uab.filter(state__in = [ UserAssignmentBinding.ST_COLLECTED, UserAssignmentBinding.ST_SUBMITTED ], user__in = students):
            b.extract2correct()
            correct.append(b.user)
    return correct

def _reassign(assignment, group_map):
    uab = UserAssignmentBinding.objects.filter(assignment = assignment)
    reassign = []
    for g, students in group_map.items():
        for b in uab.filter(state = UserAssignmentBinding.ST_READY, user__in = students):
            b.ressign()
            reassign.append(b.user)
    return reassign










@login_required
def submitform_submit(request):
    """TBA"""
    user = request.user
    logger.debug(f"user {user}, method: {request.method}")
    if request.POST.get('button') == 'apply':
        for uab_id in request.POST.getlist('selection', []):
            try:
                UserAssignmentBinding.objects.get(id = uab_id, user = user, state = UserAssignmentBinding.ST_WORKINPROGRESS).collect(submit = True)
                #FIXME: message
            except Exception as e:
                logger.error(e)
                #FIXME: message
                raise
        return redirect('education:assignment_student')
    else:
        return redirect('education:student')




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


