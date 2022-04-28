import logging
import re
import json

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views import generic
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.db import IntegrityError

from django_tables2 import RequestConfig

from kooplexhub.lib import now

from container.models import Image, Container
from .models import UserCourseBinding, UserAssignmentBinding, Assignment, CourseContainerBinding, CourseGroup, UserCourseGroupBinding
from .forms import TableAssignment_new
from .forms import FormCourse
from .forms import FormGroup
from .forms import FormAssignment
from .forms import TableAssignment, TableAssignmentConf, TableAssignmentHandle, TableUser, TableAssignmentMass, TableAssignmentSummary, TableGroup, TableAssignmentMassAll

logger = logging.getLogger(__name__)

class TeacherCourseBindingListView(LoginRequiredMixin, generic.ListView):
    template_name = 'teacher_course_list.html'
    context_object_name = 'teachercoursebindinglist'

    def get_queryset(self):
        user = self.request.user
        profile = user.profile
        return UserCourseBinding.objects.filter(user = user, is_teacher = True)


class StudentCourseBindingListView(LoginRequiredMixin, generic.ListView):
    template_name = 'student_course_list.html'
    context_object_name = 'studentcoursebindinglist'

    def get_queryset(self):
        user = self.request.user
        profile = user.profile
        return UserCourseBinding.objects.filter(user = user, is_teacher = False)


@login_required
def configure(request, usercoursebinding_id, next_page = 'education:teacher'):
    user = request.user
    profile = user.profile
    logger.debug(f"method: {request.method}, user: {user.username}")
    try:
        course = UserCourseBinding.objects.get(id = usercoursebinding_id, user = request.user, is_teacher = True).course
    except UserCourseBinding.DoesNotExist:
        logger.error(f'abuse {user} tries to access usercoursebinding id {usercoursebinding_id}')
        messages.error(request, 'Course does not exist')
        return redirect(next_page)
    if request.POST.get('button') == 'apply':
        active_tab = request.POST.get('active_tab')
        logger.debug(f'tab: {active_tab}')

        if active_tab == 'conf':
            form_course = FormCourse(request.POST)
            if form_course.is_valid():
                course.name = form.cleaned_data['name']
                course.description = form.cleaned_data['description']
                course.image = form.cleaned_data['image']
                try:
                    course.save()
                except IntegrityError as e:
                    messages.error(request, str(e))
                else:
                    messages.error(request, form_course.errors)
        elif active_tab == 'group':
            form_group = FormGroup(request.POST)
            if form_group.is_valid():
                try:
                    form_group.save()
                    messages.info(request, f'Group {form_group.cleaned_data["name"]} for course {form_group.cleaned_data["course"].name} is created')
                except IntegrityError as e:
                    messages.error(request, str(e))
                else:
                    messages.error(request, form_group.errors)

            gids = [ x.split('-')[-1] for x in filter(lambda x: x.startswith("name-before-"), request.POST.keys()) ]
            delete_ids = request.POST.getlist('selection_group_removal', [])
            d = []
            for gid in delete_ids:
                try:
                    g = CourseGroup.objects.get(id = gid, course = course)
                    g.delete()
                    logger.info(f'- deleted g {g.name} from course {course.name} by {user.username}')
                    d.append(f'{g.name}')
                    if gid in gids:
                        gids.remove(gid)
                except Exception as e:
                    logger.error(e)
            if len(d):
                g = ', '.join(d)
                messages.info(request, f'Deleted group(s) {g}.')

            gu = []
            for g in gids:
                before_name = request.POST[f'name-before-{g}']
                after_name = request.POST[f'name-{g}']
                before_description = request.POST[f'description-before-{g}']
                after_description = request.POST[f'description-{g}']
                if (before_name == after_name) and (before_description == after_description):
                    continue
                grp = CourseGroup.objects.get(id = g, course = course)
                grp.name = after_name
                grp.description = after_description
                grp.save()
                gu.append(grp.name)
            if len(gu):
                gu = ', '.join(gu)
                messages.info(request, f'Updates group(s) {gu}.')


        return redirect(next_page)
    else:

        table_student = TableUser(course, teacher_selector = False, pattern = profile.search_education_student)
        if table_student.empty:
            profile.search_education_student = ''
            profile.save()
            table_student = TableUser(course, teacher_selector = False, pattern = '')

        table_teacher = TableUser(course, teacher_selector = True, pattern = profile.search_education_teacher)
        if table_teacher.empty:
            profile.search_education_teacher = ''
            profile.save()
            table_teacher = TableUser(course, teacher_selector = True, pattern = '')

        table_group = TableGroup(CourseGroup.objects.filter(course = course))
        form_course = FormCourse({ 'name': course.name, 'description': course.description, 'image': course.image })
        form_group = FormGroup(course = course)

        #student_group_map = { 
        #        'ungrouped': UserCourseBinding.objects.filter(course = course, is_teacher = False).exclude(usercoursegroupbinding__id__gt = 0),
        #        'groups': dict([ (g, UserCourseBinding.objects.filter(course = course, is_teacher = False, usercoursegroupbinding__group = g)) 
        #                for g in CourseGroup.objects.filter(course = course)
        #            ])
        #        }

        context_dict = {
            'courseform': form_course,
            'groupform': form_group,
            't_student': table_student,
            't_teacher': table_teacher,
            't_group': table_group,
            'usercoursebinding_id': usercoursebinding_id,
            'course': course,
            'submenu': 'meta',
            'next_page': next_page,
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
        'menu_teaching': 'active',
        'submenu': 'assignment_teacher',
    }
    courses = [ ucb.course for ucb in UserCourseBinding.objects.filter(user = user, is_teacher = True) ]
    if len(courses) == 0:
        messages.warning(request, f'You are not bound to any course as a teacher.')
        return redirect('index')

    active_tab = request.COOKIES.get('active_tab', 'tab-handle')
    request.COOKIES['active_tab'] = 'tab-conf' if active_tab == 'tab-new' else active_tab
    assignment_id_cookie = request.COOKIES.get('assignment_id', None)

    mapping = [ (c.id, Assignment.objects.filter(course = c)) for c in courses ]
    keep = lambda c: len(c[1])
    course_assignments = dict(filter(keep, mapping))
    if request.method == 'POST':
        try:
            assignment_id = int(request.POST.get('assignment_selected'))
        except ValueError:
            assignment_id = assignment_id_cookie
    else:
        assignment_id = assignment_id_cookie

    if assignment_id is None:
        for qs in course_assignments.values():
            if len(qs):
                assignment_id = qs.first().id
                break

    if assignment_id is not None:
        a = Assignment.objects.get(id = assignment_id)
        qs_uab = UserAssignmentBinding.objects.filter(assignment__id = assignment_id)
        students_handled = [ b.user for b in qs_uab ]
        uab = [ UserAssignmentBinding(user = b.user, assignment = a) for b in a.course.studentbindings if not b.user in students_handled ]
        uab.extend( qs_uab )
        context_dict.update({
            'assignment_id': assignment_id,
            't_assignments': TableAssignmentHandle( uab ),
            't_mass': TableAssignmentMass( a ),
            })
    else:
        messages.warning(request, f'You need to select the assignment.')

    assignments = Assignment.objects.filter(course__in = courses)
    table_assignment_config = TableAssignmentConf(assignments)
    table_assignment_summary = TableAssignmentSummary(assignments)

    okay = lambda f: f.okay
    assignments = set()
    for la in course_assignments.values():
        assignments.update(la)
    context_dict.update({
        'd_course_assignments': course_assignments,
        't_assignment_summary': table_assignment_summary,
        't_assignment_config': table_assignment_config,
        'f_assignment': list(filter(okay, [ FormAssignment(user = user, course = c, auto_id = f'id_newassignment_{c.cleanname}_%s') for c in courses ])),
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
    handout = _handout(assignment, groups[ex(request.POST.getlist('handout'))])
    if len(handout):
        messages.info(request, 'received: ' + ', '.join(list(map(lambda s: str(s), handout))))
    collect = _collect(assignment, groups[ex(request.POST.getlist('collect'))])
    if len(collect):
        messages.info(request, 'collected: ' + ', '.join(list(map(lambda s: str(s), collect))))
    correct = _correct(assignment, groups[ex(request.POST.getlist('correct'))])
    if len(correct):
        messages.info(request, 'corrected: ' + ', '.join(list(map(lambda s: str(s), correct))))
    reassign = _reassign(assignment, groups[ex(request.POST.getlist('reassign'))])
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
    context_dict = {
        'menu_teaching': 'active',
        'submenu': 'assignment_student',
        'next_page': 'education:assignment_student', #FIXME: get rid of it
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
    RequestConfig(request).configure(table_submit)
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
def _adduser(request, usercoursebinding_id, is_teacher):
    """
    @summary: the teacher of a course may add or remove students/teachers to the given course
              this function handles request
    """
    user = request.user
    button = request.POST.get('button')
    logger.debug(f"user {user}, method: {request.method}")
    add_user_ids = request.POST.getlist('add_uid', [])
    remove_usercoursebinding_ids = set(request.POST.getlist('bound_bid', [])).difference(request.POST.getlist('keep_bid', []))
    if button not in [ 'reset', 'apply' ]:
        return redirect('education:configure', usercoursebinding_id = usercoursebinding_id)
    try:
        course = UserCourseBinding.objects.get(id = usercoursebinding_id, user = user, is_teacher = True).course
    except UserCourseBinding.DoesNotExist:
        logger.error(f'misused by {user}')
        messages.error(request, f'Not authorized to use this functionality')
        return redirect('indexpage')

    if button == 'reset':
        ucb = UserCourseBinding.objects.filter(course = course, is_teacher = False)
        if len(ucb):
            hrn = lambda x: f"{x.user.first_name} {x.user.last_name} ({x.user.username})"
            users = ", ".join(list(map(hrn, ucb)))
            logger.info(f'- removing {len(ucb)} students from course {course.name}: {users}')
            messages.info(request, f'From course {course.name} removing students: {users}')
            ucb.delete()
        return redirect('education:configure', usercoursebinding_id = usercoursebinding_id)

    added = []
    oops = []
    f = 'teacher' if is_teacher else 'student'
    for u in User.objects.filter(id__in = add_user_ids):
        try:
            UserCourseBinding.objects.create(user = u, course = course, is_teacher = is_teacher)
            added.append(u)
            logger.info(f'+ user {u.username} bound to course {course.name} by {user.username} as {f}')
        except Exception as e:
            logger.error(e)
            oops.append(u)

    ucb = UserCourseBinding.objects.filter(id__in = remove_usercoursebinding_ids, course = course, is_teacher = is_teacher)
    removed = [ b.user for b in ucb ]
    ucb.delete()

    if len(added):
        a = ', '.join(list(map(lambda x: str(x), added)))
        messages.info(request, f'Bound {a} ({f}) to course {course.name}.')
    if len(removed):
        r = ', '.join(list(map(lambda x: str(x), removed)))
        messages.info(request, f'Removed {r} ({f}) from course {course.name}.')
        logger.info(f'- users {r} ({f}) removed from course {course.name}.')
    if len(oops):
        o = ', '.join(list(map(lambda x: str(x), oops)))
        messages.error(request, f'Problem adding {o} ({f}) to course {course.name}.')
    return redirect('education:configure', usercoursebinding_id = usercoursebinding_id)


@login_required
def addstudent(request, usercoursebinding_id):
    return _adduser(request, usercoursebinding_id, is_teacher = False)


@login_required
def addteacher(request, usercoursebinding_id):
    return _adduser(request, usercoursebinding_id, is_teacher = True)


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


@login_required
def groupstudent(request, usercoursebinding_id):
    user = request.user
    logger.debug("user %s, method: %s" % (user, request.method))
    try:
        course = UserCourseBinding.objects.get(id = usercoursebinding_id, user = user, is_teacher = True).course
        for k in filter(lambda x: x.startswith('grp-'), request.POST.keys()):
            gid = k.split('-')[1]
            if gid == 'n': continue
            group = CourseGroup.objects.get(id = gid, course = course)
            ids_before = json.loads(request.POST[f'before_grp-{gid}'])
            ids_after = json.loads(request.POST[k])
            for uid in set(ids_before).difference(ids_after):
                ucgb = UserCourseGroupBinding.objects.get(usercoursebinding__user__id = uid, group = group, usercoursebinding__course = course, usercoursebinding__is_teacher = False)
                ucgb.delete()
                #FIXME: message
        for k in filter(lambda x: x.startswith('grp-'), request.POST.keys()):
            gid = k.split('-')[1]
            if gid == 'n': continue
            group = CourseGroup.objects.get(id = gid, course = course)
            ids_before = json.loads(request.POST[f'before_grp-{gid}'])
            ids_after = json.loads(request.POST[k])
            for uid in set(ids_after).difference(ids_before):
                ucb = UserCourseBinding.objects.get(user__id = uid, course = course, is_teacher = False)
                UserCourseGroupBinding.objects.create(usercoursebinding = ucb, group = group)
                #FIXME: message
    except:
        raise
    return redirect('education:teacher')
