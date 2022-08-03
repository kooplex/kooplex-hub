import logging
import re
import json

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views import generic
from django.utils.html import format_html
from django.urls import reverse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.db import IntegrityError

from kooplexhub.lib import now

from hub.templatetags.extras import render_user
from container.models import Image, Container
from .models import UserCourseBinding, UserAssignmentBinding, Assignment, CourseContainerBinding, CourseGroup, UserCourseGroupBinding, Course
from .forms import FormCourse
from .forms import FormGroup
from .forms import FormAssignment
from .forms import TableAssignment, TableAssignmentConf, TableAssignmentHandle, TableUser, TableAssignmentMass, TableAssignmentSummary, TableGroup, TableAssignmentMassAll, TableAssignmentStudentSummary, TableCourseStudentSummary

logger = logging.getLogger(__name__)

class TeacherCourseBindingListView(LoginRequiredMixin, generic.ListView):
    template_name = 'course_list.html'
    context_object_name = 'coursebindinglist'

    def get_queryset(self):
        user = self.request.user
        profile = user.profile
        return UserCourseBinding.objects.filter(user = user, is_teacher = True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['menu_education'] = True
        context['submenu'] = 'teacher'
        context['empty_title'] = "You have not been added to any courses yet as a teacher"
        context['empty_body'] = format_html("""If this is unexpected, please ask system administrator to take care of it. <a href="mailto:kooplex@elte.hu"><i class="bi bi-envelope"></i><span>&nbsp;Send e-mail...</span></a>""")
        return context


class StudentCourseBindingListView(LoginRequiredMixin, generic.ListView):
    template_name = 'course_list.html'
    context_object_name = 'coursebindinglist'

    def get_queryset(self):
        user = self.request.user
        profile = user.profile
        return UserCourseBinding.objects.filter(user = user, is_teacher = False)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['menu_education'] = True
        context['submenu'] = 'student'
        context['empty_title'] = "You have not been added to any courses yet"
        context['empty_body'] = "If this is unexpected, please ask your professor to administer."
        return context


@login_required
def configure(request, usercoursebinding_id):
    user = request.user
    profile = user.profile
    logger.debug(f"method: {request.method}, user: {user.username}")
    try:
        course = UserCourseBinding.objects.get(id = usercoursebinding_id, user = request.user, is_teacher = True).course
    except UserCourseBinding.DoesNotExist:
        logger.error(f'abuse {user} tries to access usercoursebinding id {usercoursebinding_id}')
        messages.error(request, 'Course does not exist')
        return redirect('indexpage')
    context_dict = {
            'menu_education': True,
            'course': course,
            'usercoursebinding_id': usercoursebinding_id,
            'courseform': FormCourse({ 'name': course.name, 'description': course.description, 'image': course.image }),
            'groupform': FormGroup(),
            't_students_add': TableUser(course, user, teacher_selector = False, bind_table = False),
            't_students': TableUser(course, user, teacher_selector = False, bind_table = True),
            't_teachers_add': TableUser(course, user, teacher_selector = True, bind_table = False),
            't_teachers': TableUser(course, user, teacher_selector = True, bind_table = True),
            't_group': TableGroup(CourseGroup.objects.filter(course = course)),
            'active': request.COOKIES.get('configure_course_tab', 'student'),
            'student_group_map': course.groups,
            }
    return render(request, 'course_configure.html', context = context_dict)


@login_required
def assignment_teacher(request):
    """
    @summary: handle assignment page. 
    @param usercoursebinding_id: is set if pencil is used, defaults to None if coming from menu.
    """
    user = request.user
    profile = user.profile
    logger.debug("user %s, method: %s" % (user, request.method))
    context_dict = {
            'menu_education': True,
            'submenu': 'assignment_teacher',
            'active': request.COOKIES.get('assignment_teacher_tab', 'conf'),
            }
    courses = UserCourseBinding.objects.filter(user = user, is_teacher = True).values_list('course')
    if not courses:
        messages.warning(request, f'You are not bound to any course as a teacher.')
        return render(request, 'education_layout.html', context = context_dict)
    assignments = Assignment.objects.filter(course__in = courses)
    uabs = UserAssignmentBinding.objects.filter(assignment__in = assignments)
    mapping = [ (c, assignments.filter(course = c)) for c in courses ]
    keep = lambda c: c[1]
    course_assignments = dict(filter(keep, mapping))

    selected_assignment_id = int(request.POST.get('assignment_selected', assignments[0].id if assignments else -1))

#    if assignment_id is not None:
#        a = Assignment.objects.get(id = assignment_id)
#        qs_uab = UserAssignmentBinding.objects.filter(assignment__id = assignment_id)
#        students_handled = [ b.user for b in qs_uab ]
#        uab = [ UserAssignmentBinding(user = b.user, assignment = a) for b in a.course.studentbindings if not b.user in students_handled ]
#        uab.extend( qs_uab )
#        context_dict.update({
#            'assignment_id': assignment_id,
#            't_assignments': TableAssignmentHandle( uab ),
#            't_mass': TableAssignmentMass( a ),
#            })
#    else:
#        messages.warning(request, f'You need to select the assignment.')

    table_assignment_config = TableAssignmentConf(assignments)
    table_assignment_summary = TableAssignmentSummary(assignments)
#    ts = dict(filter(lambda i: i[1] is not None, { c.id: TableCourseStudentSummary(c) for c in courses }.items()))

#    okay = lambda f: f.okay
#    assignments = set()
#    for la in course_assignments.values():
#        assignments.update(la)
    context_dict.update({
        'd_course_assignments': course_assignments,
        't_assignment_summary': table_assignment_summary,
        #        't_course_student_summary': table_course_student_summary,
##        'ts': ts,
        't_assignment_config': table_assignment_config,
##        'f_assignment': list(filter(okay, [ FormAssignment(user = user, course = c, auto_id = f'id_newassignment_{c.cleanname}_%s') for c in courses ])),
        't_mass_all': TableAssignmentMassAll( assignments ),
        })
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
                b.state = UserAssignmentBinding.ST_WORKINPROGRESS
                b.received_at = now()
                b.save()
            except UserAssignmentBinding.DoesNotExist:
                UserAssignmentBinding.objects.create(user = s, assignment = assignment, state = UserAssignmentBinding.ST_WORKINPROGRESS)
            handout.append(s)
    return handout

def _collect(assignment, group_map):
    uab = UserAssignmentBinding.objects.filter(assignment = assignment)
    collect = []
    for g, students in group_map.items():
        for b in uab.filter(state = UserAssignmentBinding.ST_WORKINPROGRESS, user__in = students):
            b.state = UserAssignmentBinding.ST_COLLECTED
            b.submitted_at = now()
            b.save()
            collect.append(b.user)
    return collect

def _correct(assignment, group_map):
    uab = UserAssignmentBinding.objects.filter(assignment = assignment)
    correct = []
    for g, students in group_map.items():
        for b in uab.filter(state__in = [ UserAssignmentBinding.ST_COLLECTED, UserAssignmentBinding.ST_SUBMITTED ], user__in = students):
            b.state = UserAssignmentBinding.ST_CORRECTED
            b.save()
            correct.append(b.user)
    return correct

def _reassign(assignment, group_map):
    uab = UserAssignmentBinding.objects.filter(assignment = assignment)
    reassign = []
    for g, students in group_map.items():
        for b in uab.filter(state = UserAssignmentBinding.ST_READY, user__in = students):
            b.state = UserAssignmentBinding.ST_WORKINPROGRESS
            b.save()
            reassign.append(b.user)
    return reassign


@login_required
def handle_mass(request):
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


@login_required
def handle_mass_many(request):
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
def assignment_student(request, usercoursebinding_id = None):
    """
    @summary: handle assignment page. 
    @param usercoursebinding_id: is set if pencil is used, defaults to None if coming from menu.
    """
    user = request.user
    profile = user.profile
    logger.debug("user %s, method: %s" % (user, request.method))
    l = reverse('education:student')
    context_dict = {
            'menu_education': True,
            'submenu': 'assignment_student',
            'empty_title': "You have not received an assignment yet",
            'empty_body': format_html(f"""<a href="{l}"><i class="bi bi-journal-bookmark-fill"></i><span class="d-none d-sm-inline">&nbsp;list your courses</span></a>"""),
            }
    if usercoursebinding_id:
        context_dict['usercoursebinding_id'] = usercoursebinding_id
        try:
            ucb = UserCourseBinding.objects.get(id = usercoursebinding_id, user = user, is_teacher = False)
        except UserCourseBinding.DoesNotExist:
            logger.error(f"Missmatch usercoursebindingid {usercoursebinding_id} for user {user}")
            messages.error(request, 'You are not allowed to use this functionality')
            return redirect('indexpage')
        courses = [ ucb.course ]
    else:
        courses = [ ucb.course for ucb in UserCourseBinding.objects.filter(user = user, is_teacher = False) ]

    table_submit = TableAssignment(UserAssignmentBinding.objects.filter(user = request.user, assignment__course__in = courses))
    context_dict.update({
        't_submit': table_submit,
        })
    return render(request, 'assignment_student.html', context = context_dict)


@login_required
def newassignment(request):
    """
    @summary: handle creation of a new assignment
    """
    user = request.user
    logger.debug("user %s, method: %s" % (user, request.method))
    try:
        course_id = request.POST.get('course_selected')
        course = UserCourseBinding.objects.get(user = user, course__id = course_id, is_teacher = True).course
    except UserCourseBinding.DoesNotExist:
        logger.error(f'misused by {user}')
        messages.error(request, f'Not authorized to use this functionality')
        return redirect('indexpage')
    try:
        f = FormAssignment(request.POST, course = course, user = user)
        assert f.is_valid(), f.errors
        a = Assignment.objects.create(
                name = f.cleaned_data['name'],
                course = course,
                creator = user,
                description = f.cleaned_data['description'],
                folder = f.cleaned_data['folder'],#recheck existence
                valid_from = f.cleaned_data['valid_from'],
                expires_at = f.cleaned_data['expires_at'],
                can_studentsubmit = f.cleaned_data['can_studentsubmit'],
                remove_collected = f.cleaned_data['remove_collected'],
                max_number_of_files = f.cleaned_data['max_number_of_files'],
                max_size = f.cleaned_data['max_size'],
                )
        logger.info(f'+ new assignment {a.name} ({a.folder}) in course {course.name} by {user.username}')
        messages.info(request, f'Assignment {a.name} created.')
    except Exception as e:
        logger.error(e)
        raise
    return redirect('education:assignment_teacher')


@login_required
def configureassignment(request):
    """
    @summary: handle creation of a new assignment
    """
    user = request.user
    logger.debug("user %s, method: %s" % (user, request.method))
    courses = [ ucb.course for ucb in UserCourseBinding.objects.filter(user = user, is_teacher = True) ]
    delete_ids = request.POST.getlist('selection_delete', [])
    other_ids = set(request.POST.getlist('assignment_ids', [])).difference(delete_ids)
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
    m = []
    for aid in other_ids:
        try:
            a = Assignment.objects.get(id = aid, course__in = courses)
            changed = []
            for attr in [ 'name', 'description', 'valid_from', 'expires_at', 'max_size', 'max_number_of_files' ]:
                old = request.POST.get(f'{attr}-old-{aid}')
                new = request.POST.get(f'{attr}-{aid}')
                if new == "":
                    new = None
                if attr in [ 'valid_from', 'expires_at', 'max_size', 'max_number_of_files' ]:
                    if old == "":
                        old = None
                if old == new:
                    continue
                setattr(a, attr, new)
                changed.append(f'new {attr} {new}')
            if len(changed):
                a.save()
                logger.info(f'. modified assignment {a.name} ({a.folder}) from course {a.course.name} by {user.username}')
                cl = ', '.join(changed)
                m.append(f'{a.name}: {cl}')
        except Exception as e:
            logger.error(e)
            raise
    if len(m):
        cl = '; '.join(m)
        messages.info(request, f'Configured assignment(s) {cl}.')
    return redirect('education:assignment_teacher')


@login_required
def submitform_submit(request):
    """TBA"""
    user = request.user
    logger.debug(f"user {user}, method: {request.method}")
    if request.POST.get('button') == 'apply':
        for uab_id in request.POST.getlist('selection', []):
            try:
                uab = UserAssignmentBinding.objects.get(id = uab_id, user = user, state__in = [ UserAssignmentBinding.ST_WORKINPROGRESS, UserAssignmentBinding.ST_SUBMITTED ])
                uab.submit_count += 1
                uab.state = UserAssignmentBinding.ST_SUBMITTED
                uab.submitted_at = now()
                uab.save()
                #FIXME: message
            except Exception as e:
                logger.error(e)
                #FIXME: message
                raise
        return redirect('education:assignment_student')
    else:
        return redirect('education:student')


@login_required
def handleassignment(request):
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
            UserAssignmentBinding.objects.create(user = u, assignment = a, state = UserAssignmentBinding.ST_WORKINPROGRESS)
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
            uab = UserAssignmentBinding.objects.get(id = uab_id, assignment__course__in = courses, state = UserAssignmentBinding.ST_WORKINPROGRESS)
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
            uab.state = UserAssignmentBinding.ST_CORRECTED
            uab.save()
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
            uab.state = UserAssignmentBinding.ST_READY
            uab.corrected_at = now()
            uab.correction_count += 1
            uab.corrector = user
            uab.feedback_text = request.POST.get(f'feedback_text-{uab_id}')
            uab.score = request.POST.get(f'score-{uab_id}')
            uab.save()
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
            uab.state = UserAssignmentBinding.ST_WORKINPROGRESS
            uab.save()
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


@login_required
def addcontainer(request, usercoursebinding_id):
    """
    @summary: handle assignment page. 
    @param usercoursebinding_id: is set if pencil is used, defaults to None if coming from menu.
    """
    user = request.user
    logger.debug("user %s, method: %s" % (user, request.method))
    try:
        course = UserCourseBinding.objects.get(id = usercoursebinding_id, user = user).course
        container, _ = Container.objects.get_or_create(
                name = course.cleanname, 
                friendly_name = course.name,
                user = user,
                suffix = 'edu',
                image = course.image
                )
        CourseContainerBinding.objects.create(course = course, container = container)
    except:
        raise
    return redirect('container:list')


def _groupstudents(ucb, mappings):
    msgs = []
    add = {}
    for gid, v in mappings.items():
        if gid == 'n':
            continue
        group = CourseGroup.objects.get(id = gid, course = ucb.course)
        ids_before = set([ b.usercoursebinding.user.id for b in UserCourseGroupBinding.objects.filter(group = group) ])
        ids_after = set(v)
        remove = []
        ucgb = UserCourseGroupBinding.objects.filter(
            usercoursebinding__user__id__in = set(ids_before).difference(ids_after), 
            group = group, usercoursebinding__course = ucb.course, 
            usercoursebinding__is_teacher = False
        )
        if ucgb:
            msgs.append('{} removed from group {}'.format(', '.join([ render_user(b.usercoursebinding.user) for b in ucgb ]), group.name))
            ucgb.delete()
        add[group] = []
        for uid in set(ids_after).difference(ids_before):
            u = User.objects.get(id = uid)
            b = UserCourseBinding.objects.get(user = u, course = ucb.course, is_teacher = False)
            add[group].append((b, render_user(u)))
    for g, bs in add.items():
        added = []
        for b, u in bs:
            UserCourseGroupBinding.objects.create(usercoursebinding = b, group = g)
            added.append(u)
        if added:
            msgs.append('{} added to group {}'.format(', '.join(added), g.name))
    return msgs


def _manageusers(ucb, ids_after, is_teacher):
    ids_before = { b.user.id: b for b in UserCourseBinding.objects.filter(course = ucb.course, is_teacher = is_teacher) }
    ids_after = set(map(int, ids_after))
    f = 'teachers' if is_teacher else 'students'
    msgs = []
    added = []
    for i in ids_after.difference(ids_before.keys()):
        u = User.objects.get(id = i)
        try:
            UserCourseBinding.objects.create(user = u, course = ucb.course, is_teacher = is_teacher)
            added.append(render_user(u))
        except Exception as e:
            logger.error(e)
    if len(added):
        added = ', '.join(added)
        msgs.append(f'Added {f} to course {ucb.course.name}: {added}')
        logger.info(f'+ user {ucb.user.username} added {added} as {f} to course {ucb.course.name}')
    bindings = UserCourseBinding.objects.filter(course = ucb.course, is_teacher = is_teacher, user__id__in = set(ids_before.keys()).difference(ids_after))
    if bindings:
        removed = ', '.join([ render_user(b.user) for b in bindings ])
        bindings.delete()
        msgs.append(f'Removed {f} from course {ucb.course.name}: {removed}')
        logger.info(f'- user {ucb.user.username} removed {removed} {f} from course {ucb.course.name}')
    return msgs


@login_required
def configure_save(request, usercoursebinding_id):
    user = request.user
    profile = user.profile
    logger.debug(f"method: {request.method}, user: {user.username}")
    try:
        binding = UserCourseBinding.objects.get(id = usercoursebinding_id, user = request.user, is_teacher = True)
        course = binding.course
    except UserCourseBinding.DoesNotExist:
        logger.error(f'abuse {user} tries to access usercoursebinding id {usercoursebinding_id}')
        messages.error(request, 'Course does not exist')
        return redirect('indexpage')

    # handle meta
    info = []
    form_course = FormCourse(request.POST)
    if form_course.is_valid():
        course.name = form_course.cleaned_data['name']
        course.description = form_course.cleaned_data['description']
        course.image = form_course.cleaned_data['image']
        course.save()
        info.append(f"Configured {course.name}") #TODO: save only changed, and report changes

    # handle teachers, students
    info.extend( _manageusers(binding, request.POST.getlist('teacher-ids'), is_teacher = True) )
    info.extend( _manageusers(binding, request.POST.getlist('student-ids'), is_teacher = False) )

    # handle groups
    bindings = CourseGroup.objects.filter(course = course, id__in = request.POST.getlist('selection_group_removal'))
    if bindings:
        info.append('Removed groups {}'.format(', '.join([ b.name for b in bindings])))
        bindings.delete()
    form_group = FormGroup(request.POST)
    if form_group.is_valid():
        g = CourseGroup.objects.create(course = course, name = form_group.cleaned_data['name'], description = form_group.cleaned_data['description'])
        info.append(f'New group {g.name} is created')
    m = []
    for gi in map(lambda x: x.split('-')[-1], filter(lambda x: x.startswith('group-name-before-'), request.POST.keys())):
        nb = request.POST[f'group-name-before-{gi}']
        na = request.POST[f'group-name-after-{gi}']
        db = request.POST[f'group-description-before-{gi}']
        da = request.POST[f'group-description-after-{gi}']
        if na and da and ((nb != na) or (db != da)):
            g = CourseGroup.objects.get(id = gi, course = course)
            g.name = na
            g.description = da
            g.save()
            m.append(g.name)
    if m:
        info.append('Modified groups: {}.'.format(', '.join(m)))

    # handle students in group
    mapping = { k: json.loads(request.POST[f'grp-{k}']) for k in map(lambda x: x.split('-')[-1], filter(lambda x: x.startswith('grp-'), request.POST.keys())) }
    info.extend( _groupstudents(binding, mapping) )
        
    if info:
        messages.info(request, ' '.join(info))

    return redirect('education:configure', usercoursebinding_id)
